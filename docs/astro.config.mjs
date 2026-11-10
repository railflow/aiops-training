// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLinksValidator from 'starlight-links-validator';

export default defineConfig({
	site: 'http://localhost:4321',
	integrations: [
		starlight({
			title: 'aiops-training',
			description: 'Scripts, Dockerfiles, manifests and sample code for the AI Ops Academy course, one folder per lesson day.',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/railflow/aiops-training' }],
			// The pages show http://localhost:... URLs on purpose.
			plugins: [starlightLinksValidator({ errorOnLocalLinks: false })],
			sidebar: [
				{ label: 'Start here', items: ['getting-started', 'tools', 'homework'] },
				{ label: 'Lesson days', items: [{ autogenerate: { directory: 'days' } }] },
			],
		}),
	],
});
