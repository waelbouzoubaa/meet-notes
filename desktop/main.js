const { app, BrowserWindow, ipcMain, desktopCapturer, systemPreferences } = require('electron');
const path = require('path');

// VPS API endpoint — change this to your VPS URL before building
const API_URL = process.env.KAPTNOTES_API_URL || 'http://localhost:8000';

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    backgroundColor: '#0A1628',
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// ── Audio capture — system audio + mic ────────────────────────────────────────
ipcMain.handle('get-audio-sources', async () => {
  const sources = await desktopCapturer.getSources({ types: ['screen', 'window'] });
  return sources.map(s => ({ id: s.id, name: s.name, thumbnail: s.thumbnail.toDataURL() }));
});

ipcMain.handle('get-api-url', () => API_URL);

// Request mic permission on macOS
ipcMain.handle('request-mic-permission', async () => {
  if (process.platform === 'darwin') {
    return await systemPreferences.askForMediaAccess('microphone');
  }
  return true;
});
