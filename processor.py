import datetime
import tempfile
import threading
import time
import json
from scipy.io.wavfile import write

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
            if not task_id or not text_to_speak:
                raise Exception("Missing task_id or text_to_speak")
            print(f"Processing Task: id={task_id}, time={datetime.datetime.now(datetime.UTC).isoformat()}")
            
            with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
                temp_filename = temp_file.name
                s3.download_file("ai-presenter", f"tasks/{task_id}.wav", temp_filename)
                reference_audios = [temp_filename]
                
                outputs = model.synthesize(
                    text_to_speak,
                    config,
                    speaker_wav=reference_audios,
                    gpt_cond_len=3,
                    language="en",
                )
                
                with tempfile.NamedTemporaryFile(suffix=".wav") as temp_upload_file:
                    write(temp_upload_file.name, 24000, outputs["wav"])
                    s3.upload_fileobj(temp_upload_file, "ai-presenter", f"results/{task_id}.wav", ExtraArgs={'ContentType': "audio/wav"})
            print(f"Successfully processed result, time={datetime.datetime.now(datetime.UTC).isoformat()}")
        except Exception as e:
            print(f"Failed to process task: {e}")
            continue

if __name__ == '__main__':
    print("Starting up...")
    threading.Thread(target=processQueue, daemon=True).start()
    while True:
        time.sleep(10)
