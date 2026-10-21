const express = require('express')
const jwt = require('jsonwebtoken')
const { exec } = require('child_process')
const session = require('express-session')
const app = express()
app.use(session({ secret: 'x', cookie: { secure: false } }))

app.post('/login', (req, res) => {
  const token = jwt.sign({ user: req.body.user }, 'key')
  res.send(token)
})

app.get('/users/:id/orders', (req, res) => {
  db.query('SELECT * FROM orders WHERE user_id = ' + req.params.id)
  exec('ls ' + req.query.dir)
  res.send('<div>' + req.query.q + '</div>')
})
