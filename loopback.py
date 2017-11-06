import time, math, sys, argparse
import pyaudio, alsaaudio, audioop
from multiprocessing import Process, Queue
from gcloud.credentials import get_credentials
from google.cloud.speech.v1beta1 import cloud_speech_pb2
from google.rpc import code_pb2
from grpc.beta import implementations

class stdout:
	BOLD = "\033[1m"
	END = "\033[0m"
	CLEAR = "\033[2K"

def bold(string):
	return stdout.BOLD + string + stdout.END

def printr(string):
	sys.stdout.write("\r" + stdout.CLEAR)
	sys.stdout.write(string)
	sys.stdout.flush()

queue = Queue()
frames = []
should_finish_stream = False

class Result:
	def __init__(self):
		self.transcription = ""
		self.confidence = ""
		self.is_final = False
		self.success = False

recognition_result = Result()

def reading_audio_loop(queue):
	recorder = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, device="pulse")
	recorder.setchannels(1)
	recorder.setrate(args.sampling_rate)
	recorder.setformat(alsaaudio.PCM_FORMAT_S16_LE)
	recorder.setperiodsize(1024)

	while True:
		length, data = recorder.read()
		if length > 0:
			queue.put(data)

def make_channel(host, port):
	ssl_channel = implementations.ssl_channel_credentials(None, None, None)
	creds = get_credentials().create_scoped(args.speech_scope)
	auth_header = ("authorization", "Bearer " + creds.get_access_token().access_token)
	auth_plugin = implementations.metadata_call_credentials(lambda _, func: func([auth_header], None), name="google_creds")
	composite_channel = implementations.composite_channel_credentials(ssl_channel, auth_plugin)
	return implementations.secure_channel(host, port, composite_channel)

def listen_loop(recognize_stream):
	global should_finish_stream
	global recognition_result

	for resp in recognize_stream:
		if resp.error.code != code_pb2.OK:
			raise RuntimeError(resp.error.message)

		for result in resp.results:
			for alt in result.alternatives:
				recognition_result.transcription = alt.transcript
				recognition_result.confidence = alt.confidence
				recognition_result.stability = result.stability
				printr(" ".join((alt.transcript, "	", "stability: ", str(int(result.stability * 100)), "%")))

			if result.is_final:
				recognition_result.is_final = True
				recognition_result.success = True
				should_finish_stream = True
				return

def request_stream():
	global queue
	global recognition_result
	global should_finish_stream

	recognition_config = cloud_speech_pb2.RecognitionConfig(
		encoding=args.audio_encoding,
		sample_rate=args.sampling_rate,
		language_code=args.lang_code,
		max_alternatives=1,
	)
	streaming_config = cloud_speech_pb2.StreamingRecognitionConfig(
		config=recognition_config,
		interim_results=True, 
		single_utterance=True
	)

	yield cloud_speech_pb2.StreamingRecognizeRequest(streaming_config=streaming_config)

	frame_length = int(args.sampling_rate * args.frame_seconds)
	frame = b""

	while True:
		if should_finish_stream:
			return

		try:
			data = queue.get(False)
			frame += data
		except Exception as e:
			if len(frame) > frame_length:
				rms = audioop.rms(frame, 2)
				decibel = 20 * math.log10(rms) if rms > 0 else 0
				if decibel < args.silent_decibel:
					recognition_result.success = False
					return
				yield cloud_speech_pb2.StreamingRecognizeRequest(audio_content=frame)
				frame = b""
			time.sleep(args.frame_seconds / 4)

def main():
	global queue
	global should_finish_stream

	preloading_process = Process(target=reading_audio_loop, args=[queue])
	preloading_process.start()

	while True:
		should_finish_stream = False

		with cloud_speech_pb2.beta_create_Speech_stub(make_channel(args.host, args.ssl_port)) as service:
			listen_loop(service.StreamingRecognize(request_stream(), args.deadline_seconds))
			if recognition_result.success:
				printr(" ".join((bold(recognition_result.transcription), "	", "confidence: ", str(int(recognition_result.confidence * 100)), "%")))
				print()


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--sampling-rate", "-rate", type=int, default=16000)
	parser.add_argument("--lang-code", "-lang", type=str, default="ja-JP")
	parser.add_argument("--audio-encoding", "-encode", type=str, default="LINEAR16")
	parser.add_argument("--frame-seconds", "-fsec", type=float, default=0.1, help="1フレームあたりの時間（秒）. デフォルトは100ミリ秒")
	parser.add_argument("--deadline-seconds", "-dsec", type=int, default=60*3+5)
	parser.add_argument("--silent-decibel", "-decibel", type=int, default=20)
	parser.add_argument("--speech-scope", "-scope", type=str, default="https://www.googleapis.com/auth/cloud-platform")
	parser.add_argument("--ssl-port", "-port", type=int, default=443)
	parser.add_argument("--host", "-host", type=str, default="speech.googleapis.com")
	args = parser.parse_args()
	main()