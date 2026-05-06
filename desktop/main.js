const { app, BrowserWindow, ipcMain, desktopCapturer, systemPreferences, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

const API_URL = process.env.KAPTNOTES_API_URL || 'http://localhost:8000';

function getConfigPath() {
  return path.join(app.getPath('userData'), 'kaptnotes-config.json');
}
function getConfig() {
  try { return JSON.parse(fs.readFileSync(getConfigPath(), 'utf8')); } catch { return {}; }
}
function setConfig(key, value) {
  const cfg = getConfig();
  cfg[key] = value;
  fs.writeFileSync(getConfigPath(), JSON.stringify(cfg));
}

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    backgroundColor: '#0A1628',
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  mainWindow.once('ready-to-show', async () => {
    mainWindow.show();
    // Ask for permissions on first launch
    if (!getConfig()['permissions-granted']) {
      await askPermissions();
    }
  });
}

async function askPermissions() {
  const { response } = await dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'KaptNotes — Autorisation requise',
    message: 'KaptNotes a besoin de vos autorisations',
    detail: 'Pour fonctionner, KaptNotes doit :\n\n• Enregistrer votre microphone\n• Enregistrer l\'audio de votre ordinateur (réunions Teams, Meet…)\n\nCes enregistrements ne sont jamais envoyés sans votre action. Vous pouvez révoquer ces droits à tout moment.',
    buttons: ['Autoriser', 'Annuler'],
    defaultId: 0,
    cancelId: 1,
  });

  if (response === 0) {
    if (process.platform === 'darwin') {
      await systemPreferences.askForMediaAccess('microphone');
    }
    setConfig('permissions-granted', true);
  }
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

// ── Auto-select primary screen source ─────────────────────────────────────────
ipcMain.handle('get-primary-source', async () => {
  const sources = await desktopCapturer.getSources({ types: ['screen'] });
  return sources[0] ? { id: sources[0].id, name: sources[0].name } : null;
});

ipcMain.handle('get-api-url', () => API_URL);
