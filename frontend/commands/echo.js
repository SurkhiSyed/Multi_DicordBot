const { SlashCommandBuilder } = require('discord.js');
const fetch = require('node-fetch'); // npm install node-fetch@2

module.exports = {
    data: new SlashCommandBuilder()
        .setName('echo')
        .setDescription('Ask the Python backend to echo your message!')
        .addStringOption(option =>
            option.setName('text')
                .setDescription('Text to echo')
                .setRequired(true)),
    async execute(interaction) {
        const text = interaction.options.getString('text');
        try {
            const response = await fetch('http://localhost:5000/api/echo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            await interaction.reply(data.response);
        } catch (error) {
            await interaction.reply('Failed to contact Python backend.');
        }
    },
};