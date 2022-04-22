module.exports = {
  darkMode: 'media',
  purge: {
    enabled: process.env.NODE_ENV == "production",
    content: ['../../ovpn_portal/templates/**/*.html'],
  }
}
