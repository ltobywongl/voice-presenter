from io import BytesIO
import threading
import time
import json

print("Importing XTTS")

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

print("Imported XTTS")

from redis import Redis
import boto3

print("Initializing Model")

# AI Setup
config = XttsConfig()
config.load_json("./XTTS-v2/config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="./XTTS-v2/")

print("Initialized")

# AWS Setup
queue = Redis(host="default-redis-0001-001.7zh2ph.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
session = boto3.Session(region_name="us-east-1")
s3 = session.client("s3")

def processQueue():
    while True:
        try:
            _, task_json = queue.blpop("tasks")
            task = json.loads(task_json)
            task_id = task["id"]
            text_to_speak = task["text"]
            print(f"Processing Task: id={task_id}, text={text_to_speak}")
            s3.download_file("ai-presenter", f"tasks/{task_id}.wav", f"./tmp/{task_id}.wav")
            reference_audios = [f"./tmp/{task_id}.wav"]
        except Exception as e:
            print(f"Failed to retrieve data: {e}")
            continue

        try:
            outputs = model.synthesize(
                text_to_speak,
                config,
                speaker_wav=reference_audios,
                gpt_cond_len=3,
                language="en",
            )
        except Exception as e:
            print(f"Failed to process: {e}")
            continue
            
        try:
            fileobj = BytesIO(outputs['wav'])
            s3.upload_fileobj(fileobj, "ai-presenter", f"results/{task_id}.wav", ExtraArgs={'ContentType': "audio/wav"})
        except Exception as e:
            print(f"Failed to upload result: {e}")
            continue

if __name__ == '__main__':
    print("Starting up...")
    threading.Thread(target=processQueue, daemon=True).start()
    while True:
        time.sleep(10)
