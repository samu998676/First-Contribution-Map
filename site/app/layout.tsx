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
const siteUrl = isGitHubPages
  ? 'https://samu998676.github.io/First-Contribution-Map/'
  : 'https://first-contribution-map.oai-x-carahs-7465.chatgpt.site/';
const socialImageUrl = new URL(
  isGitHubPages ? 'og.png' : '/og.png',
  siteUrl,
).toString();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: 'First Contribution Map',
  description:
    'Turn a public GitHub repository into a newcomer-friendly project map with likely architecture and approachable first-contribution candidates.',
  openGraph: {
    title: 'First Contribution Map',
    description:
      'Understand a repository and find your first meaningful pull request.',
    type: 'website',
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
    description:
      'Understand a repository and find your first meaningful pull request.',
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
