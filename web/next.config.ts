import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  env:{
    NEXT_PUBLIC_API_PORT: process.env.NEXT_PUBLIC_API_PORT ?? "how are you" ,  
  }
};

module.exports = {
  output: 'standalone'
}

export default nextConfig;
