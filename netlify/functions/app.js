const serverless = require('serverless-http');
const app = require('./app-wrapper');

module.exports.handler = serverless(app);
