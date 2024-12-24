import os
import time
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from PIL import Image
import random

def create_random_image(size=(1024, 768)):
    # 创建随机图片
    image = Image.new('RGB', size)
    pixels = image.load()
    
    # 生成渐变随机图案
    for x in range(size[0]):
        for y in range(size[1]):
            r = int((x / size[0]) * random.randint(0, 255))
            g = int((y / size[1]) * random.randint(0, 255))
            b = random.randint(0, 255)
            pixels[x, y] = (r, g, b)
    
    # 保存为PNG，适度压缩
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG', optimize=True, quality=95)
    img_byte_arr.seek(0)
    
    # 打印当前图片大小
    size_mb = img_byte_arr.getbuffer().nbytes / 1024 / 1024
    print(f"Generated image size: {size_mb:.2f}MB")
    return img_byte_arr, size_mb

def main():
    # 连接到 MinIO
    client = Minio(
        os.environ.get("MINIO_HOST", "minio:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        secure=False
    )

    bucket_name = "test-bucket"

    # 确保 bucket 存在
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Created bucket: {bucket_name}")
    except S3Error as err:
        print(f"Error creating bucket: {err}")
        return

    count = 0
    total_size = 0

    while True:
        try:
            # 生成随机图片
            img_data, img_size = create_random_image()
            total_size += img_size
            
            # 上传图片
            client.put_object(
                bucket_name,
                f"image_{count}.png",
                img_data,
                img_data.getbuffer().nbytes,
                content_type="image/png"
            )
            print(f"Successfully uploaded image_{count}.png")
            print(f"Total uploaded size: {total_size:.2f}MB")
            count += 1
            time.sleep(1)  # 每次上传间隔1秒

        except S3Error as err:
            print(f"Error uploading: {err}")
            if "NoSuchBucket" in str(err):
                print("Bucket doesn't exist")
                break
            elif "QuotaExceeded" in str(err) or "insufficient space" in str(err).lower():
                print("Storage quota exceeded")
                print(f"Total files uploaded: {count}")
                print(f"Total size uploaded: {total_size:.2f}MB")
                break
            else:
                print(f"Unexpected error: {err}")
                time.sleep(5)  # 其他错误等待5秒后重试
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()