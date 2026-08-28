import type { NextConfig } from 'next';

const isGitHubPages = process.env.GITHUB_PAGES === 'true';

const nextConfig: NextConfig = isGitHubPages
  ? {
      output: 'export',
      basePath: '/First-Contribution-Map',
      assetPrefix: '/First-Contribution-Map/',
      trailingSlash: true,
      images: { unoptimized: true },
    }
  : {};

export default nextConfig;
