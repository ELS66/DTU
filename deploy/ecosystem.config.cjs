const path = require('node:path');

module.exports = {
  apps: [
    {
      name: 'dtu-api',
      cwd: path.resolve(__dirname, '../backend'),
      script: 'dist/main.js',
      interpreter: process.env.NODE_BIN || process.execPath,
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      autorestart: true,
      env: {
        NODE_ENV: 'production',
        HOST: '127.0.0.1',
        PORT: process.env.PORT || '7926',
      },
    },
  ],
};
