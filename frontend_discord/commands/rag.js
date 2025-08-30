const { SlashCommandBuilder } = require('discord.js');
const fetch = require('node-fetch'); // npm install node-fetch@2

module.exports = {
    data: new SlashCommandBuilder()
        .setName('rag')
        .setDescription('Ask the RAG model chatbot your questions about AI PMAccelerator!')
        .addStringOption(option =>
            option.setName('question')
                .setDescription('Ask question to RAG')
                .setRequired(true)),
    async execute(interaction) {
        const question = interaction.options.getString('question');
        await interaction.deferReply(); // Show "thinking..." in Discord

        try {
            const response = await fetch('http://localhost:8000/api/rag', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: question })
            });
        
            // Check for non-JSON response
            const text = await response.text();
        
            let data;
            try {
                data = JSON.parse(text);
            } catch (jsonErr) {
                console.error("❌ Failed to parse JSON:", text);
                return await interaction.editReply('⚠️ Python backend did not return valid JSON.');
            }
        
            // Try to extract just the content='...' part if present
            let answer = data.response;
            const contentMatch = answer.match(/content='([^']+)'/);
            if (contentMatch) {
                answer = contentMatch[1];
            }
        
            let reply = `**Q:** ${question}\n`;
            reply += `**A:** ${answer}\n\n`;
        
            if (data.matches && data.matches.length > 0) {
                reply += `__**Thinking Process:**__\n`;
                data.matches.slice(0, 3).forEach((match, idx) => {
                    reply += `**[${idx + 1}]**\n`;
                    reply += `> **Score:** ${match.score.toFixed(2)}\n`;
                    reply += `> **Source:** ${match.metadata?.source || 'N/A'}\n`;
                    reply += `> **Content:** ${match.content.slice(0, 200)}\n\n`;
                });
            }
        
            if (data.sources && data.sources.length > 0) {
                reply += '**Sources:**\n' + data.sources
                    .filter(Boolean)
                    .map((src, idx) => `> [${idx + 1}] ${src}`)
                    .join('\n');
            }
        
            const MAX_DISCORD_LENGTH = 2000;
            if (reply.length > MAX_DISCORD_LENGTH) {
                reply = reply.slice(0, MAX_DISCORD_LENGTH - 20) + '\n...[truncated]';
            }
        
            await interaction.editReply(reply);
        } catch (error) {
            console.error("❌ Fetch Error:", error);
            await interaction.editReply('❌ Failed to contact Python backend.');
        }
        
    },
};