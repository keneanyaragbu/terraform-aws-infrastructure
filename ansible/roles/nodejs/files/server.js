const http = require('http');
const os = require('os');

const hostname = os.hostname();
const port = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/html');
  res.end(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Production App</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          background: linear-gradient(135deg, #1a237e, #0d47a1);
          color: white;
          text-align: center;
          padding: 50px;
          margin: 0;
        }
        .card {
          background: rgba(255,255,255,0.1);
          border-radius: 15px;
          padding: 40px;
          max-width: 600px;
          margin: 0 auto;
          box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        p { font-size: 1.1em; opacity: 0.9; }
        .badge {
          display: inline-block;
          background: #00e676;
          color: #000;
          padding: 5px 15px;
          border-radius: 20px;
          font-weight: bold;
          margin: 5px;
        }
      </style>
    </head>
    <body>
      <div class="card">
        <h1>Hello from AWS!</h1>
        <p>Deployed by: <strong>Anyaragbu Kenechukwu</strong></p>
        <p>Server: <strong>${hostname}</strong></p>
        <p>Domain: <strong>kaydev.online</strong></p>
        <br>
        <span class="badge">Terraform</span>
        <span class="badge">Ansible</span>
        <span class="badge">AWS</span>
        <span class="badge">Node.js</span>
      </div>
    </body>
    </html>
  `);
});

server.listen(port, '0.0.0.0', () => {
  console.log(`Server running on port ${port}`);
});
