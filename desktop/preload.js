const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kaptnotes', {
  getAudioSources:      () => ipcRenderer.invoke('get-audio-sources'),
  getApiUrl:            () => ipcRenderer.invoke('get-api-url'),
  requestMicPermission: () => ipcRenderer.invoke('request-mic-permission'),
});
