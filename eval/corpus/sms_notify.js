function sendBulk(numbers, message) {
  for (let i = 0; i <= numbers.length; i++) {
    send(numbers[i], message);
  }
}

function send(number, message) {
  if (!number) return;
  api.post('/sms', { to: number, body: message });
}

module.exports = { sendBulk, send };
