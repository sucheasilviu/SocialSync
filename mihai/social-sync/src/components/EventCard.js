import React from 'react';
import { Calendar, MapPin, DollarSign, ExternalLink } from 'lucide-react';

const EventCard = ({ event }) => {
  return (
    <div className="bg-gray-50 border-l-4 border-red-500 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow flex-1 min-w-[300px] mb-4">
      <h3 className="text-lg font-bold text-gray-900 mb-2">🏆 {event.title}</h3>
      
      <div className="space-y-2 text-sm text-gray-700">
        <div className="flex items-center gap-2">
          <Calendar size={16} className="text-red-500" />
          <span className="font-semibold">When:</span> {event.date}
        </div>
        
        <div className="flex items-center gap-2">
          <MapPin size={16} className="text-red-500" />
          <span className="font-semibold">Where:</span> {event.location}
        </div>

        <div className="flex items-center gap-2">
          <DollarSign size={16} className="text-red-500" />
          <span className="font-semibold">Cost:</span> {event.cost}
        </div>
      </div>

      <p className="mt-3 text-gray-600 italic text-sm border-t pt-2 border-gray-200">
        "{event.description}"
      </p>

      <a 
        href={event.url} 
        target="_blank" 
        rel="noopener noreferrer"
        className="mt-4 inline-flex items-center gap-2 text-red-600 font-bold hover:underline"
      >
        <ExternalLink size={16} />
        View Event Details
      </a>
    </div>
  );
};

export default EventCard;