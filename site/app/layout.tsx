import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

const isGitHubPages = process.env.GITHUB_PAGES === 'true';
const canonicalSiteUrl =
  'https://samu998676.github.io/First-Contribution-Map/';
const siteUrl = isGitHubPages
  ? canonicalSiteUrl
  : 'https://first-contribution-map.oai-x-carahs-7465.chatgpt.site/';
const socialImageUrl = new URL('og.png', canonicalSiteUrl).toString();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  applicationName: 'First Contribution Map',
  title: 'First Contribution Map',
  description:
    'Turn a public GitHub repository into a clear project summary, likely architecture map, and three beginner-friendly contribution paths.',
  keywords: [
    'open source',
    'GitHub',
    'first contribution',
    'good first issue',
    'repository analysis',
    'developer onboarding',
  ],
  creator: 'samu998676',
  category: 'developer tools',
  alternates: {
    canonical: canonicalSiteUrl,
  },
  openGraph: {
    title: 'First Contribution Map',
    description: 'Understand a repository. Find your first meaningful PR.',
    type: 'website',
    url: canonicalSiteUrl,
    siteName: 'First Contribution Map',
    images: [
      {
        url: socialImageUrl,
        width: 1200,
        height: 630,
        alt: 'First Contribution Map — Understand a repository. Find your first meaningful PR.',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'First Contribution Map',
    description: 'Understand a repository. Find your first meaningful PR.',
    images: [socialImageUrl],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
