const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kaptnotes', {
  getPrimarySource: () => ipcRenderer.invoke('get-primary-source'),
  getApiUrl:        () => ipcRenderer.invoke('get-api-url'),
});
