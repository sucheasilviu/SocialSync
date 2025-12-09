import React from 'react';
import { Calendar, MapPin, DollarSign, ExternalLink, Trophy } from 'lucide-react';

const EventCard = ({ event }) => {
  return (
    <div className="group relative bg-gray-800/50 border-y border-r border-gray-700 border-l-[6px] border-l-emerald-500 rounded-xl p-4 w-full md:w-[48%] flex flex-col gap-3 hover:bg-gray-800 transition shadow-lg overflow-hidden">
      
      {/* HEADER */}
      <div className="flex items-start gap-2">
        <Trophy className="text-yellow-500 flex-shrink-0 mt-1" size={18} />
        <h3 className="text-lg font-bold text-gray-100 leading-tight">
          {event.title}
        </h3>
      </div>

      {/* DETAILS */}
      <div className="flex flex-col gap-2 text-sm text-gray-300">
        
        {/* Date */}
        <div className="flex items-center gap-2">
          <Calendar className="text-emerald-400" size={16} />
          <span>
            <span className="font-semibold text-gray-500">When: </span> 
            {event.date}
          </span>
        </div>

        {/* Location */}
        <div className="flex items-start gap-2">
          <MapPin className="text-emerald-400 mt-0.5" size={16} />
          <span>
            <span className="font-semibold text-gray-500">Where: </span> 
            {event.location}
          </span>
        </div>

        {/* Cost */}
        <div className="flex items-center gap-2">
          <DollarSign className="text-emerald-400" size={16} />
          <span>
            <span className="font-semibold text-gray-500">Cost: </span> 
            {event.cost}
          </span>
        </div>
      </div>

      {/* DESCRIPTION */}
      <div className="mt-1 text-xs italic text-gray-500 border-t border-gray-700 pt-2">
        "{event.description}"
      </div>

      {/* LINK */}
      <a
        href={event.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto flex items-center gap-2 text-emerald-400 font-bold hover:text-emerald-300 transition-colors uppercase text-xs tracking-wide"
      >
        <ExternalLink size={14} /> View Event Details
      </a>
    </div>
  );
};

export default EventCard;