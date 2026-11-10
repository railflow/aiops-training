const _ = require("lodash");
const moment = require("moment");
const { v4: uuidv4 } = require("uuid");

console.log(_.capitalize("hello from node"), "at", moment().format("YYYY-MM-DD HH:mm"), "id", uuidv4());
