import numpy as np
import sounddevice as sd


class AudioEngine:

    def __init__(self):

        self.blocksize = 1024
        self.samplerate = 44100

        self.stream = sd.InputStream(
            channels=1,
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            callback=self.callback
        )

        self.audio_buffer = np.zeros(self.blocksize)

        self.stream.start()


    def callback(self, indata, frames, time, status):

        self.audio_buffer = indata[:,0]


    def get_spectrum(self):

        fft = np.abs(np.fft.rfft(self.audio_buffer))

        fft = fft / np.max(fft + 1e-6)

        return fft
