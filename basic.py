from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

from IPython.display import Audio
from scipy.io.wavfile import write

config = XttsConfig()
config.load_json("./XTTS-v2/config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="./XTTS-v2/")
model.cuda() # Use GPU, comment out if no GPU is available

text_to_speak = "Present with AI now! Start, Stop and record"
reference_audios = ["./input.wav"]

outputs = model.synthesize(
    text_to_speak,
    config,
    speaker_wav=reference_audios,
    gpt_cond_len=3,
    language="en",
)

output_file_path = f'./output.wav'
write(output_file_path, 24000, outputs['wav'])
