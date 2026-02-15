import React from 'react';
import './MainLayout.css';

export interface MainLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children, className }) => {
  return (
    <div className={`main-layout ${className || ''}`}>
      <main className="main-content">{children}</main>
    </div>
  );
};
