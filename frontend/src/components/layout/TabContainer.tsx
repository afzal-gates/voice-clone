import React from 'react';
import './TabContainer.css';

export interface TabContainerProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export const TabContainer: React.FC<TabContainerProps> = ({ children, className, id }) => {
  return (
    <div
      id={id}
      role="tabpanel"
      className={`tab-container ${className || ''}`}
      tabIndex={0}
    >
      {children}
    </div>
  );
};
