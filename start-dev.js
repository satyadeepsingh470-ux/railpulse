import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🚀 Starting RailPulse Hybrid Ecosystem (FastAPI + Baileys Bridge + Vite React)...');

// 1. Start WhatsApp Baileys Microservice (Port 3001)
const bridgeProcess = spawn('node', ['index.js'], {
  cwd: path.resolve(__dirname, 'whatsapp-bridge'),
  stdio: 'inherit',
  shell: true
});

// 2. Start FastAPI Backend (Port 8000)
const venvUvicorn = path.resolve(__dirname, 'backend/.venv/bin/uvicorn');
const fastapiProcess = spawn(venvUvicorn, ['main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'], {
  cwd: path.resolve(__dirname, 'backend'),
  stdio: 'inherit',
  shell: true
});

// 3. Start Vite React Client (Port 5173)
const clientProcess = spawn('npm', ['run', 'dev'], {
  cwd: path.resolve(__dirname, 'client'),
  stdio: 'inherit',
  shell: true
});

function cleanup() {
  console.log('\n🛑 Shutting down all processes (Bridge, FastAPI, Client)...');
  try { bridgeProcess.kill('SIGINT'); } catch {}
  try { fastapiProcess.kill('SIGINT'); } catch {}
  try { clientProcess.kill('SIGINT'); } catch {}
  process.exit(0);
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
