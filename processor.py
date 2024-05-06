from io import BytesIO
import threading
import time
import json

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

# from IPython.display import Audio
# from scipy.io.wavfile import write

from redis import StrictRedis
import boto3

# AI Setup
config = XttsConfig()
config.load_json("./XTTS-v2/config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="./XTTS-v2/")
model.cuda()

# AWS Setup
queue = StrictRedis(host="ai-presenter-7zh2ph.serverless.use1.cache.amazonaws.com", port=6379)
session = boto3.Session(region_name="us-east-1")
s3 = session.client("s3")

def processQueue():
    while True:
        try:
            _, task_json = queue.blpop("tasks")
            task = json.loads(task_json)
            task_id = task["id"]
            text_to_speak = task["text"]
            s3.download_file("ai-presenter", f"tasks/{task_id}.wav", f"tasks/{task_id}.wav")
            reference_audios = [f"./tasks/{task_id}.wav"]
            
            outputs = model.synthesize(
                text_to_speak,
                config,
                speaker_wav=reference_audios,
                gpt_cond_len=3,
                language="en",
            )
            
            fileobj = BytesIO(outputs['wav'])
            s3.upload_fileobj(fileobj, "ai-presenter", f"results/{task_id}.wav", ExtraArgs={'ContentType': "audio/wav"})
        except:
            print(f"Failed to process.")
            continue

if __name__ == '__main__':
    threading.Thread(target=processQueue, daemon=True).start()
    while True:
        time.sleep(10)
