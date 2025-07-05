import pika
import os
import json
import logging
import time
import traceback
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# Default RabbitMQ connection parameters (can be overridden by environment variables)
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672)) # pika expects port as int
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '/')

# Exchange details (as per plan.md)
DEFAULT_EXCHANGE_NAME = 'deepsoc_notifications_exchange'
DEFAULT_EXCHANGE_TYPE = 'topic'

class RabbitMQPublisher:
    def __init__(self, host=RABBITMQ_HOST, port=RABBITMQ_PORT,
                 username=RABBITMQ_USER, password=RABBITMQ_PASSWORD,
                 virtual_host=RABBITMQ_VHOST, max_retries=5, retry_delay=5):
        self.credentials = pika.PlainCredentials(username, password)
        self.parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=virtual_host,
            credentials=self.credentials,
            heartbeat=600,  # Keep connection alive, helps with some firewalls
            blocked_connection_timeout=300 # How long to wait before failing a connection
        )
        self.connection = None
        self.channel = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay # seconds
        self._connect()

    def _connect(self):
        # First, cleanly close any existing connection/channel if they exist and are broken
        if self.channel and (self.channel.is_closed or not self.connection or self.connection.is_closed):
            try:
                if self.channel.is_open: self.channel.close()
            except Exception as e: logger.warning(f"Error closing previous RabbitMQ channel: {e}")
            self.channel = None
        if self.connection and self.connection.is_closed:
            try:
                if self.connection.is_open: self.connection.close()
            except Exception as e: logger.warning(f"Error closing previous RabbitMQ connection: {e}")
            self.connection = None

        # If connection and channel are already fine, do nothing
        if self.connection and self.connection.is_open and self.channel and self.channel.is_open:
            return

        retries = 0
        while retries < self.max_retries:
            try:
                logger.info(f"Attempting to connect to RabbitMQ (host: {self.parameters.host}, port: {self.parameters.port}, attempt {retries + 1}/{self.max_retries})...")
                self.connection = pika.BlockingConnection(self.parameters)
                self.channel = self.connection.channel()
                
                # Optional: Enable publisher confirms for higher reliability as per plan.
                # To use confirms, you'd typically make the channel transactional or use confirm_delivery()
                # and then check the return value of basic_publish.
                # For now, keeping it simpler. It can be added if message loss becomes an issue.
                # self.channel.confirm_delivery() 
                # logger.info("RabbitMQ publisher confirms enabled (if uncommented).")

                logger.info("Successfully connected to RabbitMQ and opened a channel.")
                return # Connection successful
            except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError) as e:
                logger.error(f"RabbitMQ connection/channel error (attempt {retries + 1}): {e}")
                # Clean up potentially broken connection object before retrying
                if self.connection and not self.connection.is_closed:
                    try: self.connection.close()
                    except: pass # Best effort
                self.connection = None
                self.channel = None
                
                retries += 1
                if retries < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Max retries reached. Failed to connect to RabbitMQ.")
                    raise  # Re-raise the last exception
            except Exception as e_generic: # Catch any other unexpected errors during connection
                logger.error(f"An unexpected error occurred during RabbitMQ connection (attempt {retries+1}): {e_generic}")
                logger.error(traceback.format_exc())
                retries +=1
                if retries < self.max_retries:
                     time.sleep(self.retry_delay)
                else:
                    logger.error("Max retries reached for unexpected error. Failed to connect to RabbitMQ.")
                    raise


    def ensure_connection(self):
        """Ensures the connection and channel are open, reconnecting if necessary."""
        if not self.connection or self.connection.is_closed or \
           not self.channel or self.channel.is_closed:
            logger.warning("RabbitMQ connection or channel is closed/unavailable. Attempting to reconnect...")
            self._connect()

    def publish_message(self, message_body, routing_key,
                        exchange_name=DEFAULT_EXCHANGE_NAME,
                        exchange_type=DEFAULT_EXCHANGE_TYPE,
                        content_type='application/json',
                        persistent=True):
        """
        Publishes a message to RabbitMQ.

        Args:
            message_body (str or dict): The message payload. If dict, will be JSON-serialized.
            routing_key (str): The routing key for the message.
            exchange_name (str): The name of the exchange. Defaults to DEFAULT_EXCHANGE_NAME.
            exchange_type (str): The type of the exchange. Defaults to DEFAULT_EXCHANGE_TYPE.
            content_type (str): The content type of the message.
            persistent (bool): Whether the message should be persistent.
        """
        self.ensure_connection() # Make sure we have an active connection and channel

        body_to_publish = None
        properties = None

        try:
            # Declare the exchange (idempotent operation, good practice)
            # This ensures the exchange exists before publishing. Durable=True means it survives broker restarts.
            self.channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=True)
            logger.debug(f"Exchange '{exchange_name}' of type '{exchange_type}' declared (or ensured exists).")

            if isinstance(message_body, dict):
                body_to_publish = json.dumps(message_body)
            elif isinstance(message_body, str):
                body_to_publish = message_body
            else:
                logger.error(f"Unsupported message_body type: {type(message_body)}. Must be dict or str.")
                raise ValueError("message_body must be a dictionary or a JSON string.")

            properties = pika.BasicProperties(
                content_type=content_type,
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE if persistent else pika.spec.TRANSIENT_DELIVERY_MODE
            )

            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=body_to_publish,
                properties=properties
            )
            # Note: For publisher confirms, basic_publish would need to be handled differently,
            # e.g., in a confirm_delivery mode, it returns a boolean or raises on failure.
            logger.info(f"Message published to exchange '{exchange_name}' (type: '{exchange_type}') with routing_key '{routing_key}'.")

        except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelClosedByBroker, pika.exceptions.StreamLostError) as conn_err:
            logger.error(f"RabbitMQ connection error during publish: {conn_err}. Attempting to reconnect and retry once.")
            self._connect() # Try to reconnect
            try:
                # Re-declare exchange just in case channel was new
                self.channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=True)
                self.channel.basic_publish(
                    exchange=exchange_name,
                    routing_key=routing_key,
                    body=body_to_publish, # Use the already prepared body
                    properties=properties  # Use the already prepared properties
                )
                logger.info("Message re-published successfully after reconnection.")
            except Exception as e_retry:
                logger.error(f"Failed to re-publish message after reconnection: {e_retry}")
                logger.error(traceback.format_exc())
                raise # Re-raise exception if retry also fails
        except Exception as e:
            logger.error(f"An unexpected error occurred while publishing message: {e}")
            logger.error(traceback.format_exc())
            raise

    def close(self):
        """Closes the RabbitMQ channel and connection if they are open."""
        closed_channel = False
        if self.channel and self.channel.is_open:
            try:
                self.channel.close()
                logger.info("RabbitMQ channel closed.")
                closed_channel = True
            except Exception as e:
                logger.warning(f"Error closing RabbitMQ channel: {e}")
        
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
                logger.info("RabbitMQ connection closed.")
            except Exception as e:
                logger.warning(f"Error closing RabbitMQ connection: {e}")
        
        # Ensure they are None if closed or were never opened properly
        if closed_channel: self.channel = None
        if (self.connection and self.connection.is_closed) or not self.connection : self.connection = None


# Example usage (primarily for testing this utility directly)
if __name__ == '__main__':
    # Configure basic logging for testing
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s'
    )
    # To test connection errors, you might stop RabbitMQ service temporarily.
    
    publisher = None
    try:
        logger.info("--- Test Case 1: Basic publish ---")
        publisher = RabbitMQPublisher()
        test_message_1 = {'event': 'test_event_1', 'data': 'Hello from mq_utils.py!', 'timestamp': time.time()}
        publisher.publish_message(
            message_body=test_message_1,
            routing_key='notifications.frontend.test.type1' # Example routing key
        )
        logger.info("Test Case 1: Message published.")

        logger.info("--- Test Case 2: Publish another message ---")
        test_message_2 = {'event': 'test_event_2', 'info': 'Another one', 'timestamp': time.time()}
        publisher.publish_message(
            message_body=test_message_2,
            routing_key='notifications.frontend.otherevent.type2'
        )
        logger.info("Test Case 2: Message published.")

        # logger.info("--- Test Case 3: Test connection drop (manual intervention needed) ---")
        # print("Please stop RabbitMQ service now to test reconnection and retry...")
        # time.sleep(10) # Time to stop the service
        # try:
        #     test_message_3 = {'event': 'test_event_3', 'critical': 'After outage attempt', 'timestamp': time.time()}
        #     publisher.publish_message(
        #         message_body=test_message_3,
        #         routing_key='notifications.frontend.critical.type3'
        #     )
        #     logger.info("Test Case 3: Message published (should have reconnected).")
        # except Exception as e_case3:
        #     logger.error(f"Test Case 3: Failed as expected or unexpectedly: {e_case3}")
        # print("Please restart RabbitMQ service now.")
        # time.sleep(5)
        # publisher.ensure_connection() # Try to ensure connection again
        # logger.info(f"Connection status after restart: channel open = {publisher.channel.is_open if publisher.channel else 'N/A'}")


    except pika.exceptions.AMQPConnectionError as amqp_err:
        logger.error(f"Main test script: AMQP Connection Error: {amqp_err}")
        logger.error("Ensure RabbitMQ is running and accessible with correct credentials.")
    except Exception as e:
        logger.error(f"Main test script: An unexpected error occurred: {e}")
        logger.error(traceback.format_exc())
    finally:
        if publisher:
            publisher.close()
        logger.info("--- Test script finished ---") 