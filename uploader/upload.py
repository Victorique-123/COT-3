import os
import time
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from PIL import Image
import random
import logging
from datetime import datetime

# 配置日志
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def create_random_image(size=(1024, 768), logger=None):
    start_time = time.time()
    logger.info(f"Starting to generate image of size {size}")
    
    image = Image.new('RGB', size)
    pixels = image.load()
    
    # 生成渐变随机图案
    for x in range(size[0]):
        for y in range(size[1]):
            r = int((x / size[0]) * random.randint(0, 255))
            g = int((y / size[1]) * random.randint(0, 255))
            b = random.randint(0, 255)
            pixels[x, y] = (r, g, b)
    
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG', optimize=True, quality=95)
    img_byte_arr.seek(0)
    
    size_mb = img_byte_arr.getbuffer().nbytes / 1024 / 1024
    generation_time = time.time() - start_time
    logger.info(f"Image generated: {size_mb:.2f}MB in {generation_time:.2f} seconds")
    
    return img_byte_arr, size_mb

def main():
    logger = setup_logging()
    logger.info("Starting MinIO upload script")
    
    # 打印环境信息
    logger.info(f"Connecting to MinIO at {os.environ.get('MINIO_HOST', 'minio:9000')}")
    
    client = Minio(
        os.environ.get("MINIO_HOST", "minio:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        secure=False
    )

    bucket_name = "test-bucket"
    logger.info(f"Using bucket: {bucket_name}")

    # 确保 bucket 存在
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"Created new bucket: {bucket_name}")
        else:
            logger.info(f"Bucket {bucket_name} already exists")
    except S3Error as err:
        logger.error(f"Error creating/checking bucket: {err}")
        return

    count = 0
    total_size = 0
    start_time = time.time()

    while True:
        try:
            # 生成随机图片
            logger.info(f"=== Starting upload cycle {count + 1} ===")
            img_data, img_size = create_random_image(logger=logger)
            total_size += img_size
            
            # 上传前记录时间
            upload_start = time.time()
            
            # 上传图片
            client.put_object(
                bucket_name,
                f"image_{count}.png",
                img_data,
                img_data.getbuffer().nbytes,
                content_type="image/png"
            )
            
            upload_time = time.time() - upload_start
            logger.info(f"Upload successful: image_{count}.png")
            logger.info(f"Upload time: {upload_time:.2f} seconds")
            logger.info(f"Current statistics:")
            logger.info(f"  - Files uploaded: {count + 1}")
            logger.info(f"  - Total size: {total_size:.2f}MB")
            logger.info(f"  - Average size per file: {(total_size/(count + 1)):.2f}MB")
            
            elapsed_time = time.time() - start_time
            logger.info(f"  - Upload rate: {(total_size/elapsed_time):.2f}MB/s")
            
            count += 1
            logger.info("Waiting 1 second before next upload...")
            time.sleep(1)

        except S3Error as err:
            logger.error(f"S3 Error occurred: {err}")
            if "NoSuchBucket" in str(err):
                logger.error("Bucket doesn't exist")
                break
            elif "QuotaExceeded" in str(err) or "insufficient space" in str(err).lower():
                logger.warning("Storage quota exceeded")
                logger.info("Final statistics:")
                logger.info(f"  - Total files uploaded: {count}")
                logger.info(f"  - Total size uploaded: {total_size:.2f}MB")
                logger.info(f"  - Time elapsed: {elapsed_time:.2f} seconds")
                logger.info(f"  - Average upload rate: {(total_size/elapsed_time):.2f}MB/s")
                break
            else:
                logger.error(f"Unexpected S3 error: {err}")
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)
        
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
