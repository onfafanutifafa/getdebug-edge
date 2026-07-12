function resetToken() {
  return Math.random().toString(36).substring(2, 10);
}
module.exports = { resetToken };
