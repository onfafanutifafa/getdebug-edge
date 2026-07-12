app.get('/api/order/:id', async (req, res) => {
  const order = await Order.findById(req.params.id);
  res.json(order);
});
