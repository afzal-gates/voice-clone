/**
 * Search Filter Component
 *
 * Filter voices by category and search term
 */

import React from 'react';
import { Input } from '@/components/ui/Input';
import type { VoiceCategory } from '@/types/realtime.types';

interface SearchFilterProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  selectedCategory: VoiceCategory;
  onCategoryChange: (category: VoiceCategory) => void;
}

export const SearchFilter: React.FC<SearchFilterProps> = ({
  searchTerm,
  onSearchChange,
  selectedCategory,
  onCategoryChange,
}) => {
  const categories: { value: VoiceCategory; label: string }[] = [
    { value: 'all', label: 'All Voices' },
    { value: 'realistic', label: 'Realistic' },
    { value: 'character', label: 'Character' },
    { value: 'custom', label: 'Custom' },
  ];

  return (
    <div className="search-filter">
      <Input
        type="text"
        placeholder="Search voices..."
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        className="search-filter__input"
      />

      <div className="search-filter__categories">
        {categories.map((category) => (
          <button
            key={category.value}
            className={`search-filter__category ${
              selectedCategory === category.value ? 'search-filter__category--active' : ''
            }`}
            onClick={() => onCategoryChange(category.value)}
          >
            {category.label}
          </button>
        ))}
      </div>
    </div>
  );
};
