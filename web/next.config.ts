import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  env:{
    NEXT_PUBLIC_SERVER_URL: process.env.NEXT_PUBLIC_SERVER_URL ?? "" ,  
  }
};

module.exports = {
  output: 'standalone'
}

export default nextConfig;
