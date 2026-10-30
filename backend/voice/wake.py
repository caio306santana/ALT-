"""Local "Hey Jarvis" detection with openWakeWord's pretrained ONNX models (melspectrogram ->
speech embedding -> wake word), run directly on onnxruntime so the ALT does not ship scipy and
scikit-learn just to import the openwakeword package. The pretrained models are CC BY-NC-SA 4.0:
personal use. Audio is processed in memory and never stored."""
from collections import deque
import numpy as np

CHUNK=1280  # 80 ms at 16 kHz, the unit the models were trained on
BASE_URL='https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/'
FILES={'melspectrogram.onnx':BASE_URL+'melspectrogram.onnx','embedding_model.onnx':BASE_URL+'embedding_model.onnx','hey_jarvis_v0.1.onnx':BASE_URL+'hey_jarvis_v0.1.onnx'}

class WakeWord:
    def __init__(self,directory,threshold=.5):
        import onnxruntime as ort
        options=ort.SessionOptions();options.inter_op_num_threads=1;options.intra_op_num_threads=1
        session=lambda name:ort.InferenceSession(str(directory/name),options,providers=['CPUExecutionProvider'])
        self.mel,self.embed,self.model=session('melspectrogram.onnx'),session('embedding_model.onnx'),session('hey_jarvis_v0.1.onnx')
        self.frames=self.model.get_inputs()[0].shape[1];self.threshold=threshold
        self.reset()

    def melspectrogram(self,samples):
        spec=np.squeeze(self.mel.run(None,{'input':samples[None,:].astype(np.float32)})[0])
        return spec/10+2  # transform that matches Google's speech_embedding front end

    def embeddings(self,spec):
        windows=[spec[i:i+76] for i in range(0,spec.shape[0]-75,8)]
        return self.embed.run(None,{'input_1':np.array(windows,dtype=np.float32)[...,None]})[0].reshape(len(windows),96)

    def reset(self):
        self.raw=deque(maxlen=16000*10);self.spec=np.ones((76,32),dtype=np.float32)
        # Start from the embedding of faint noise, as openWakeWord does, so silence does not score.
        noise=np.random.default_rng(0).integers(-1000,1000,16000*4).astype(np.int16)
        self.features=self.embeddings(self.melspectrogram(noise))

    def feed(self,chunk):
        """One 1280-sample int16 chunk -> wake word score (0-1)."""
        self.raw.extend(chunk.tolist())
        recent=np.array(list(self.raw)[-CHUNK-480:],dtype=np.int16)
        self.spec=np.vstack((self.spec,self.melspectrogram(recent)))[-970:]
        window=self.spec[-76:].astype(np.float32)[None,:,:,None]
        self.features=np.vstack((self.features,self.embed.run(None,{'input_1':window})[0].reshape(1,96)))[-120:]
        return float(self.model.run(None,{self.model.get_inputs()[0].name:self.features[-self.frames:][None].astype(np.float32)})[0].squeeze())

    def detect(self,chunk):
        score=self.feed(chunk)
        if score>=self.threshold:self.reset();return True,score
        return False,score
