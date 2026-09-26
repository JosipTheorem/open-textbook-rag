class Capture extends AudioWorkletProcessor {
  constructor() { super(); this.pending = []; }
  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;
    // Browser audio is commonly 48 kHz. Downsample to the ASR's 16 kHz.
    const ratio = sampleRate / 16000;
    for (const sample of channel) this.pending.push(sample);
    const count = Math.floor(this.pending.length / ratio);
    if (count < 320) return true;
    const output = new Int16Array(count);
    for (let i = 0; i < count; i++) {
      const x = Math.max(-1, Math.min(1, this.pending[Math.floor(i * ratio)]));
      output[i] = x < 0 ? x * 32768 : x * 32767;
    }
    this.pending = this.pending.slice(Math.floor(count * ratio));
    this.port.postMessage(output.buffer, [output.buffer]);
    return true;
  }
}
registerProcessor('capture', Capture);
