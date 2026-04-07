const express = require('express');
const { exec } = require('child_process');
const app = express();
const PORT = 3333;

app.use(express.json());

// Ejecutar comando de TV
app.post('/tv/command', (req, res) => {
  const { command } = req.body;
  if (!command) return res.status(400).json({ error: 'No command' });
  
  console.log('Executing:', command);
  
  exec(command, { cwd: '/home/santi21435/.n8n', timeout: 30000 }, (error, stdout, stderr) => {
    if (error) {
      return res.status(500).json({ 
        error: error.message, 
        stdout, 
        stderr,
        success: false 
      });
    }
    res.json({ 
      success: true, 
      stdout: stdout.trim(),
      command 
    });
  });
});

// Health check
app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.listen(PORT, '127.0.0.1', () => {
  console.log(`TV Bridge running on port ${PORT}`);
});
