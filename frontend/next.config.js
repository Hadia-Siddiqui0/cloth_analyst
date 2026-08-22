/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // No ESLint config exists in this project yet. Without this, `next build`
  // tries to prompt interactively to set one up -- on Vercel's non-interactive
  // build machine, that prompt has no one to answer it and the build just
  // hangs forever with no error message. This unblocks the build now;
  // adding a real .eslintrc later (and removing this line) is worth doing
  // once there's time, but isn't urgent.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

module.exports = nextConfig;
