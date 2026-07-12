const fs = require('fs');
const path = require('path');

function readUserFile(req, res) {
  const filename = req.query.name;
  const filepath = '/var/uploads/' + filename;
  fs.readFile(filepath, 'utf8', (err, data) => {
    res.send(data);
  });
}

module.exports = { readUserFile };
