const purgecss = require('@fullhuman/postcss-purgecss')

module.exports = {
  plugins: [
    purgecss({
      content: ['./src/**/*.js', './node_modules/bootstrap/**/*.js', './node_modules/reactstrap/**/*.js']
    })
  ]
};