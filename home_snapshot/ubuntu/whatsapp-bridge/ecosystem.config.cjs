module.exports = {
  apps: [{
    name: 'whatsapp-bridge',
    script: 'index.js',
    interpreter: 'node',
    cwd: '/home/ubuntu/whatsapp-bridge',
    env: {
      PORT: '8002',
      SESSION_DIR: '/home/ubuntu/whatsapp-bridge/sessions/default',
      WEBHOOK_URL: 'http://localhost:9001/webhook/melissa_2026',
      WEBHOOK_TOKEN: '',
      LOG_LEVEL: 'info',
      PHONE_NUMBER: '573236263207'
    }
  }]
}
