const fs = require('fs');
const https = require('https');
const path = require('path');

// Create libs directory
const libsDir = path.join(__dirname, 'libs');
if (!fs.existsSync(libsDir)) {
    fs.mkdirSync(libsDir);
}

// Download Bootstrap CSS
https.get('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css', (response) => {
    const file = fs.createWriteStream(path.join(libsDir, 'bootstrap.min.css'));
    response.pipe(file);
    console.log('Bootstrap CSS downloaded');
});

// Download Bootstrap JS
https.get('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js', (response) => {
    const file = fs.createWriteStream(path.join(libsDir, 'bootstrap.bundle.min.js'));
    response.pipe(file);
    console.log('Bootstrap JS downloaded');
});