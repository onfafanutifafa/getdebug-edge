async function withRetry(fn, max = 3) {
  for (let attempt = 0; attempt < max; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (attempt === max - 1) throw err;
      await new Promise(r => setTimeout(r, 2 ** attempt * 100));
    }
  }
}
module.exports = { withRetry };
