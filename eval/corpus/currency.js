const RATES = { GHS: 1.0, NGN: 0.011, KES: 0.075, USD: 15.6 };

function toGhs(amount, currency) {
  const rate = RATES[currency];
  if (rate === undefined) {
    throw new Error(`Unsupported currency: ${currency}`);
  }
  return Math.round(amount * rate * 100) / 100;
}

module.exports = { toGhs, RATES };
