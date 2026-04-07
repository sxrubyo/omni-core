const lgtv = require('lgtv2')({
    url: 'wss://192.168.0.4:3001',
    timeout: 10000,
    reconnect: false,
    keyFile: '/home/santi21435/.n8n/lg_key'
});

lgtv.on('connect', () => {
    console.log('\n✅ ¡CONECTADO! Nexus Mainframe tiene acceso.');
    lgtv.disconnect();
    process.exit(0);
});

lgtv.on('error', (err) => {
    console.log('\n❌ Error de conexión:', err.message);
    process.exit(1);
});

lgtv.on('prompt', () => {
    console.log('\n📺 ¡MIRA LA TELE! Acepta el cuadro de diálogo ahora.');
});
