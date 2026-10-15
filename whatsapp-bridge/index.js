import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import QRCode from 'qrcode';
import pino from 'pino';
import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion
} from '@whiskeysockets/baileys';

const app = express();
const PORT = process.env.PORT || 3001;
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const authDir = path.resolve('./auth_info_baileys');

app.use(cors());
app.use(express.json());

const logger = pino({ level: 'silent' });
let sock = null;
let status = 'disconnected'; // 'disconnected' | 'qr_ready' | 'connecting' | 'connected'
let qrDataUrl = null;
let connectedUser = null;

async function initSocket() {
  try {
    status = 'connecting';
    const { state, saveCreds } = await useMultiFileAuthState(authDir);
    const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: [2, 3000, 1015901307] }));

    sock = makeWASocket({
      version,
      logger,
      printQRInTerminal: false,
      auth: state,
      browser: ['IRCTC Tracker Bridge', 'Chrome', '1.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
      if (qr) {
        status = 'qr_ready';
        qrDataUrl = await QRCode.toDataURL(qr, { margin: 2, scale: 8 });
        console.log('📱 [Baileys Bridge] New QR code generated');
      }

      if (connection === 'close') {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const reconnect = statusCode !== DisconnectReason.loggedOut;
        console.log(`🔌 [Baileys Bridge] WhatsApp closed (${statusCode}). Reconnecting: ${reconnect}`);
        status = 'disconnected';
        qrDataUrl = null;
        connectedUser = null;
        if (reconnect) setTimeout(initSocket, 3000);
      } else if (connection === 'open') {
        status = 'connected';
        qrDataUrl = null;
        const id = sock.user?.id || '';
        const name = sock.user?.name || sock.user?.notify || 'Bot Admin';
        const cleanPhone = id.split(':')[0] || id.split('@')[0];
        connectedUser = { id, phone: cleanPhone, name };
        console.log(`✅ [Baileys Bridge] Connected to WhatsApp: +${cleanPhone} (${name})`);
      }
    });

    // Forward incoming WhatsApp messages to FastAPI webhook
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
      if (type !== 'notify') return;
      for (const msg of messages) {
        if (!msg.message || msg.key.fromMe) continue;
        const jid = msg.key.remoteJid;
        if (!jid || jid.endsWith('@g.us')) continue;

        const text = (msg.message.conversation || msg.message.extendedTextMessage?.text || '').trim();
        const senderPhone = jid.split('@')[0].replace(/\D/g, '');
        if (!text) continue;

        console.log(`📩 [Baileys Bridge] Inbound message from +${senderPhone}: "${text}"`);
        try {
          const res = await fetch(`${FASTAPI_URL}/api/whatsapp/webhook`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ senderPhone, text, jid })
          });
          const data = await res.json();
          if (data?.reply) {
            await sock.sendMessage(jid, { text: data.reply });
          }
        } catch (err) {
          console.warn('⚠️ Webhook forwarding to FastAPI failed:', err.message);
        }
      }
    });
  } catch (err) {
    console.error('Error starting Baileys socket:', err);
    status = 'disconnected';
  }
}

// 1. Get connection status and QR code
app.get('/qr', (req, res) => {
  res.json({
    status,
    qrDataUrl,
    connectedUser,
    timestamp: new Date().toISOString()
  });
});

// 2. Send outgoing WhatsApp message
app.post('/send', async (req, res) => {
  const { phone, message } = req.body;
  const cleanPhone = (phone || '').replace(/\D/g, '');
  const jid = `${cleanPhone}@s.whatsapp.net`;

  if (sock && status === 'connected' && cleanPhone.length >= 10) {
    try {
      await sock.sendMessage(jid, { text: message });
      console.log(`📤 [Baileys Bridge] WhatsApp message delivered to +${cleanPhone}`);
      return res.json({ success: true, status: 'DELIVERED' });
    } catch (err) {
      console.error(`Failed to deliver message to +${cleanPhone}:`, err.message);
      return res.json({ success: false, status: 'FAILED', error: err.message });
    }
  }

  // If WhatsApp is not connected, log as SIMULATED
  console.log(`ℹ️ [Baileys Bridge] Simulated alert for +${cleanPhone} (WhatsApp not paired)`);
  res.json({ success: true, status: 'SIMULATED' });
});

// 3. Reconnect / Refresh QR
app.post('/reconnect', async (req, res) => {
  try {
    if (sock) sock.end();
  } catch {}
  initSocket();
  res.json({ success: true, message: 'Reconnecting...' });
});

// 4. Disconnect / Logout
app.post('/disconnect', async (req, res) => {
  try {
    if (sock) await sock.logout();
    if (fs.existsSync(authDir)) fs.rmSync(authDir, { recursive: true, force: true });
  } catch {}
  status = 'disconnected';
  qrDataUrl = null;
  connectedUser = null;
  res.json({ success: true, message: 'Disconnected' });
});

app.listen(PORT, () => {
  console.log(`⚡ WhatsApp Baileys Microservice running on http://localhost:${PORT}`);
  initSocket();
});
