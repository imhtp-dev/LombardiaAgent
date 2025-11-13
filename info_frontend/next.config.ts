import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone', // Enable standalone build for Docker
  typescript:{
    ignoreBuildErrors:true
  },
  
};

export default nextConfig;
