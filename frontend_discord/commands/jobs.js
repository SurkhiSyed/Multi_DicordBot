const { SlashCommandBuilder } = require('discord.js');
const fetch = require('node-fetch'); // Make sure this is imported

module.exports = {
    data: new SlashCommandBuilder()
        .setName('jobs')
        .setDescription('Search for jobs on LinkedIn')
        .addStringOption(option =>
            option.setName('keywords')
                .setDescription('Job keywords to search for (e.g., "intern", "software engineer")')
                .setRequired(true))
        .addStringOption(option =>
            option.setName('linkedin_username')
                .setDescription('Your LinkedIn username/email')
                .setRequired(true))
        .addStringOption(option =>
            option.setName('linkedin_password')
                .setDescription('Your LinkedIn password')
                .setRequired(true))
        .addIntegerOption(option =>
            option.setName('num_jobs')
                .setDescription('Number of jobs to scrape (default: 56)')
                .setRequired(false)),
    
    async execute(interaction) {
        const keywords = interaction.options.getString('keywords');
        const linkedin_username = interaction.options.getString('linkedin_username');
        const linkedin_password = interaction.options.getString('linkedin_password');
        const num_jobs = interaction.options.getInteger('num_jobs') || 56;

        // Use deferReply like rag.js because scraping takes time
        await interaction.deferReply({ ephemeral: true }); // ephemeral for privacy

        try {
            const response = await fetch('http://localhost:8000/api/jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    linkedin_username: linkedin_username,
                    linkedin_password: linkedin_password,
                    num_jobs: num_jobs
                }),
            });

            // Parse response like rag.js
            const text = await response.text();

            let data;
            try {
                data = JSON.parse(text);
            } catch (jsonErr) {
                console.error("❌ Failed to parse JSON:", text);
                return await interaction.editReply('⚠️ Backend did not return valid JSON.');
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${data.error || 'Unknown error'}`);
            }

            // Handle the response
            if (data.success && data.jobs && data.jobs.length > 0) {
                let reply = `🎯 **Found ${data.total_jobs} jobs for "${keywords}":**\n\n`;
                
                // Show first 5 jobs to avoid Discord message limits
                const jobsToShow = data.jobs.slice(0, 5);
                
                jobsToShow.forEach((job, idx) => {
                    reply += `**${idx + 1}.** ${job.name}\n`;
                    reply += `🏢 **Company:** ${job.company}\n`;
                    reply += `📍 **Location:** ${job.location}\n`;
                    reply += `💼 **Type:** ${job.job_type}\n`;
                    if (job.application_link) {
                        reply += `🔗 **Apply:** ${job.application_link}\n`;
                    }
                    reply += `\n`;
                });

                if (data.total_jobs > 5) {
                    reply += `\n_... and ${data.total_jobs - 5} more jobs! Check the full list in your CSV file._`;
                }

                // Discord message limit check
                const MAX_DISCORD_LENGTH = 2000;
                if (reply.length > MAX_DISCORD_LENGTH) {
                    reply = reply.slice(0, MAX_DISCORD_LENGTH - 20) + '\n...[truncated]';
                }

                await interaction.editReply(reply);
            } else {
                await interaction.editReply(`❌ ${data.error || 'No jobs found for your search.'}`);
            }

        } catch (error) {
            console.error('❌ Error fetching jobs:', error);
            await interaction.editReply('❌ Sorry, there was an error fetching the jobs. Please try again.');
        }
    }
};