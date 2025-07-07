import pika
import os
import json
import logging
import time
import threading
import traceback
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# RabbitMQ connection parameters from environment variables
# 强制使用IPv4地址，避免IPv6连接尝试
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', '127.0.0.1')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '/')

DEFAULT_EXCHANGE_NAME = 'deepsoc_notifications_exchange' # Should match publisher
DEFAULT_EXCHANGE_TYPE = 'topic'
DEFAULT_QUEUE_NAME = 'deepsoc_frontend_notifications_queue'
DEFAULT_ROUTING_KEY = 'notifications.frontend.#' # Capture all frontend notifications

class RabbitMQConsumer:
    def __init__(self, host=RABBITMQ_HOST, port=RABBITMQ_PORT,
                 username=RABBITMQ_USER, password=RABBITMQ_PASSWORD,
                 virtual_host=RABBITMQ_VHOST,
                 exchange_name=DEFAULT_EXCHANGE_NAME,
                 exchange_type=DEFAULT_EXCHANGE_TYPE,
                 queue_name=DEFAULT_QUEUE_NAME,
                 routing_key=DEFAULT_ROUTING_KEY,
                 max_retries=5, retry_delay=5):
        self.credentials = pika.PlainCredentials(username, password)
        self.parameters = pika.ConnectionParameters(
            host=host, port=port,
            virtual_host=virtual_host, credentials=self.credentials,
            heartbeat=600, # Keep connection alive
            blocked_connection_timeout=300,
            socket_timeout=10  # 设置socket超时，加快失败检测
        )
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._connection = None
        self._channel = None
        self._consumer_tag = None
        self.is_consuming = False
        self._user_callback = None
        self._connect_lock = threading.Lock() # To prevent multiple connection attempts simultaneously

    def _connect(self):
        if self._connection and self._connection.is_open:
            return True
        
        with self._connect_lock:
            if self._connection and self._connection.is_open:
                 return True # Double check after acquiring lock

            logger.info(f"Consumer: Attempting to connect to RabbitMQ at {self.parameters.host}:{self.parameters.port}...")
            retries = 0
            while retries < self.max_retries:
                try:
                    self._connection = pika.BlockingConnection(self.parameters)
                    self._channel = self._connection.channel()
                    logger.info("Consumer: Successfully connected to RabbitMQ and channel opened.")
                    self._setup_exchange_queue()
                    return True
                except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelError) as e:
                    retries += 1
                    logger.error(f"Consumer: Connection/Channel attempt {retries}/{self.max_retries} failed: {e}")
                    if retries < self.max_retries:
                        logger.info(f"Consumer: Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error("Consumer: Max connection retries reached. Could not connect to RabbitMQ.")
                        return False
            return False

    def _setup_exchange_queue(self):
        if not self._channel or self._channel.is_closed:
            logger.error("Consumer: Channel is not open. Cannot setup exchange/queue.")
            return
        try:
            self._channel.exchange_declare(exchange=self.exchange_name, exchange_type=self.exchange_type, durable=True)
            self._channel.queue_declare(queue=self.queue_name, durable=True, exclusive=False, auto_delete=False)
            self._channel.queue_bind(queue=self.queue_name, exchange=self.exchange_name, routing_key=self.routing_key)
            logger.debug("Consumer: Exchange, queue, and binding setup complete.")
        except Exception as e:
            logger.error(f"Consumer: Error setting up exchange/queue: {e}")
            logger.error(traceback.format_exc())
            # Potentially try to reconnect or raise error
            if self._connection and self._connection.is_open:
                self._connection.close()
            self._connection = None # Force reconnect on next attempt
            raise # Re-raise the exception to signal failure in setup

    def _on_message(self, channel, method_frame, properties, body):
        delivery_tag = method_frame.delivery_tag
        try:
            message_str = body.decode('utf-8')
            message_dict = json.loads(message_str)
            logger.debug(f"Consumer: Received message: {message_dict.get('message_id', 'N/A')}, RK: {method_frame.routing_key}")
            if self._user_callback:
                self._user_callback(message_dict) # Pass the deserialized dict
            channel.basic_ack(delivery_tag)
            logger.debug(f"Consumer: ACKed message {delivery_tag}")
        except json.JSONDecodeError as e_json:
            logger.error(f"Consumer: Failed to decode JSON message: {body[:200]}... Error: {e_json}")
            channel.basic_nack(delivery_tag, requeue=False) # Don't requeue bad messages
        except Exception as e_callback:
            logger.error(f"Consumer: Error processing message in user callback: {e_callback}")
            logger.error(traceback.format_exc())
            # Decide on ack/nack based on error type. For now, nack and don't requeue to avoid poison pills.
            channel.basic_nack(delivery_tag, requeue=False)

    def start_consuming(self, callback_on_message):
        self._user_callback = callback_on_message
        if not self._connect():
            logger.error("Consumer: Cannot start consuming due to connection failure.")
            self.is_consuming = False
            return

        self.is_consuming = True
        logger.debug("Consumer: Starting to consume messages...")
        while self.is_consuming:
            try:
                if not self._connection or self._connection.is_closed:
                    logger.warning("Consumer: Connection lost. Attempting to reconnect...")
                    if not self._connect():
                        logger.error("Consumer: Reconnect failed. Stopping consumption attempt for now.")
                        time.sleep(self.retry_delay * 2) # Wait longer before trying to restart consuming loop
                        continue # Try to restart the consumption loop
                
                # Prefetch count for potentially better performance with multiple messages
                self._channel.basic_qos(prefetch_count=10)
                self._consumer_tag = self._channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._on_message
                    # auto_ack=False is default and correct, we do manual ack
                )
                # Blocking call that processes network events
                # 使用非阻塞方式，以便能够响应停止信号
                self._channel.start_consuming()
            except pika.exceptions.StreamLostError as e_stream_lost:
                logger.error(f"Consumer: StreamLostError during consumption: {e_stream_lost}. Will attempt to reconnect.")
                self._connection = None # Force reconnect
            except pika.exceptions.AMQPConnectionError as e_conn:
                logger.error(f"Consumer: AMQPConnectionError during consumption: {e_conn}. Will attempt to reconnect.")
                self._connection = None # Force reconnect
            except Exception as e:
                logger.error(f"Consumer: Unexpected error during consumption: {e}")
                logger.error(traceback.format_exc())
                self.is_consuming = False # Stop on unexpected major errors
                break # Exit the while loop
            
            if self.is_consuming: # If start_consuming was stopped gracefully, it will exit, otherwise try to recover
                logger.info("Consumer: Consumption was interrupted. Attempting to re-establish...")
                time.sleep(self.retry_delay)
            else:
                logger.info("Consumer: Consumption loop exiting as is_consuming is False.")

        logger.info("Consumer: Consumption stopped.")
        self._close_internals()

    def _close_internals(self):
        try:
            if self._channel and self._channel.is_open:
                if self._consumer_tag:
                    logger.info(f"Consumer: Cancelling consumer tag: {self._consumer_tag}")
                    self._channel.basic_cancel(self._consumer_tag)
                logger.info("Consumer: Closing channel.")
                self._channel.close()
            if self._connection and self._connection.is_open:
                logger.info("Consumer: Closing connection.")
                self._connection.close()
            logger.info("Consumer: Connection and channel closed.")
        except Exception as e:
            logger.error(f"Consumer: Error during close: {e}")
            logger.error(traceback.format_exc())
        finally:
            self._channel = None
            self._connection = None
            self.is_consuming = False

    def stop_consuming(self):
        logger.info("Consumer: Received stop signal.")
        self.is_consuming = False
        
        # 更强制的停止机制
        try:
            # 1. 先尝试取消consumer tag
            if self._channel and self._channel.is_open and self._consumer_tag:
                self._channel.basic_cancel(self._consumer_tag)
                logger.debug(f"Consumer: Consumer tag {self._consumer_tag} cancelled on stop.")
        except Exception as e_cancel:
            logger.error(f"Consumer: Error cancelling consumer tag on stop: {e_cancel}")
        
        try:
            # 2. 强制关闭channel
            if self._channel and self._channel.is_open:
                self._channel.close()
                logger.debug("Consumer: Channel closed forcefully.")
        except Exception as e_channel:
            logger.error(f"Consumer: Error closing channel: {e_channel}")
            
        try:
            # 3. 强制关闭connection
            if self._connection and self._connection.is_open:
                self._connection.close()
                logger.debug("Consumer: Connection closed forcefully.")
        except Exception as e_conn:
            logger.error(f"Consumer: Error closing connection: {e_conn}")
        
        # 重置状态
        self._channel = None
        self._connection = None
        self._consumer_tag = None

# Example Usage (for testing, not part of the library itself):
# def my_message_processor(message_data):
#     print(f"Received and processing: {message_data}")

# if __name__ == '__main__':
#     logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s')
#     consumer = RabbitMQConsumer(
#         host='localhost', port=5672, username='guest', password='guest', virtual_host='/'
#     )
    
#     consumer_thread = threading.Thread(target=consumer.start_consuming, args=(my_message_processor,), name="MQConsumerThread")
#     consumer_thread.daemon = True # So it exits when main thread exits
#     consumer_thread.start()
    
#     try:
#         while True:
#             time.sleep(1)
#             # Keep main thread alive, or do other work
#     except KeyboardInterrupt:
#         logger.info("Main: KeyboardInterrupt received. Stopping consumer...")
#         consumer.stop_consuming()
#         consumer_thread.join(timeout=10) # Wait for consumer thread to finish
#         logger.info("Main: Consumer stopped. Exiting.") 