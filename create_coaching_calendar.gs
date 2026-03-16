/**
 * Google Apps Script to create AP Coaching Call calendar events
 *
 * HOW TO USE:
 * 1. Go to https://script.google.com
 * 2. Create a new project
 * 3. Paste this entire script
 * 4. Click Run > createCoachingEvents
 * 5. Authorize when prompted
 * 6. Events will be created and invites sent to students
 */

function createCoachingEvents() {
  const calendar = CalendarApp.getDefaultCalendar();
  const CALL_DURATION_MINUTES = 30;
  const YEAR = 2026;
  const TIMEZONE = 'America/Chicago'; // US Central Time (Austin, TX)

  // Student email mapping
  const studentEmails = {
    'Gus Castillo': 'gus.castillo@alpha.school',
    'Emma Cotner': 'emma.cotner@alpha.school',
    'Jackson Price': 'jackson.price@alpha.school',
    'Boris Dudarev': 'boris.dudarev@alpha.school',
    'Sydney Barba': 'sydney.barba@alpha.school',
    'Branson Pfiester': 'branson.pfiester@alpha.school',
    'Saeed Tarawneh': 'said.tarawneh@alpha.school',
    'Aheli Shah': 'aheli.shah@alpha.school',
    'Ella Dietz': 'ella.dietz@alpha.school',
    'Stella Cole': 'stella.cole@alpha.school',
    'Erika Rigby': 'erika.rigby@alpha.school',
    'Grady Swanson': 'grady.swanson@alpha.school',
    'Zayen Szpitalak': 'zayen.szpitalak@alpha.school',
    'Adrienne Laswell': 'adrienne.laswell@alpha.school',
    'Austin Lin': 'austin.lin@alpha.school',
    'Jessica Owenby': 'jessica.owenby@alpha.school',
    'Cruce Saunders IV': 'cruce.saunders@alpha.school',
    'Kavin Lingham': 'kavin.lingham@alpha.school',
    'Stella Grams': 'stella.grams@alpha.school',
    'Jacob Kuchinsky': 'jacob.kuchinsky@alpha.school',
    'Luca Sanchez': 'luca.sanchez@alpha.school',
    'Ali Romman': 'ali.romman@alpha.school',
    'Benny Valles': 'benjamin.valles@alpha.school',
    'Vera Li': 'vera.li@alpha.school',
    'Emily Smith': 'emily.smith@alpha.school',
    'Paty Margain-Junco': 'paty.margainjunco@alpha.school',
    'Michael Cai': 'michael.cai@alpha.school'
  };

  // All coaching calls (excluding Tue Mar 10 - already booked)
  const calls = [
    // Week of Mar 9 (excluding today)
    { date: [3, 11], time: '09:45', student: 'Jackson Price', course: 'AP World History' },
    { date: [3, 11], time: '08:35', student: 'Boris Dudarev', course: 'AP Human Geography' },
    { date: [3, 11], time: '09:05', student: 'Sydney Barba', course: 'AP Human Geography' },
    { date: [3, 12], time: '08:00', student: 'Saeed Tarawneh', course: 'AP World History' },
    { date: [3, 12], time: '09:05', student: 'Aheli Shah', course: 'AP Human Geography' },
    { date: [3, 13], time: '10:00', student: 'Ella Dietz', course: 'AP World History' },
    { date: [3, 13], time: '10:30', student: 'Emma Cotner', course: 'AP World History' },

    // Week of Mar 16
    { date: [3, 17], time: '08:00', student: 'Stella Cole', course: 'AP World History' },
    { date: [3, 17], time: '08:45', student: 'Erika Rigby', course: 'AP Human Geography' },
    { date: [3, 16], time: '09:00', student: 'Grady Swanson', course: 'AP Human Geography' },
    { date: [3, 16], time: '08:50', student: 'Zayen Szpitalak', course: 'AP Human Geography' },
    { date: [3, 18], time: '09:40', student: 'Branson Pfiester', course: 'AP Human Geography' },
    { date: [3, 19], time: '08:20', student: 'Gus Castillo', course: 'AP Human Geography' },
    { date: [3, 19], time: '09:35', student: 'Emma Cotner', course: 'AP World History' },
    { date: [3, 20], time: '08:00', student: 'Saeed Tarawneh', course: 'AP World History' },
    { date: [3, 20], time: '08:35', student: 'Adrienne Laswell', course: 'AP Human Geography' },
    { date: [3, 20], time: '09:05', student: 'Austin Lin', course: 'AP Human Geography' },

    // Week of Mar 23
    { date: [3, 25], time: '08:00', student: 'Boris Dudarev', course: 'AP Human Geography' },
    { date: [3, 25], time: '08:35', student: 'Sydney Barba', course: 'AP Human Geography' },
    { date: [3, 26], time: '08:20', student: 'Gus Castillo', course: 'AP Human Geography' },
    { date: [3, 26], time: '09:35', student: 'Emma Cotner', course: 'AP World History' },
    { date: [3, 27], time: '08:00', student: 'Saeed Tarawneh', course: 'AP World History' },
    { date: [3, 27], time: '08:35', student: 'Jessica Owenby', course: 'AP Human Geography' },
    { date: [3, 27], time: '09:05', student: 'Cruce Saunders IV', course: 'AP US History' },

    // Week of Mar 30
    { date: [4, 1], time: '08:00', student: 'Zayen Szpitalak', course: 'AP Human Geography' },
    { date: [4, 1], time: '08:35', student: 'Stella Cole', course: 'AP World History' },
    { date: [4, 1], time: '09:10', student: 'Branson Pfiester', course: 'AP Human Geography' },
    { date: [4, 2], time: '08:20', student: 'Gus Castillo', course: 'AP Human Geography' },
    { date: [4, 2], time: '09:35', student: 'Emma Cotner', course: 'AP World History' },
    { date: [4, 3], time: '08:00', student: 'Saeed Tarawneh', course: 'AP World History' },
    { date: [4, 3], time: '08:35', student: 'Kavin Lingham', course: 'AP World History' },
    { date: [4, 3], time: '09:05', student: 'Stella Grams', course: 'AP World History' },

    // Week of Apr 6
    { date: [4, 7], time: '08:00', student: 'Sydney Barba', course: 'AP Human Geography' },
    { date: [4, 8], time: '08:00', student: 'Jacob Kuchinsky', course: 'AP Human Geography' },
    { date: [4, 8], time: '08:35', student: 'Luca Sanchez', course: 'AP Human Geography' },
    { date: [4, 8], time: '09:05', student: 'Boris Dudarev', course: 'AP Human Geography' },
    { date: [4, 9], time: '08:20', student: 'Gus Castillo', course: 'AP Human Geography' },
    { date: [4, 9], time: '08:35', student: 'Aheli Shah', course: 'AP Human Geography' },
    { date: [4, 9], time: '09:05', student: 'Ella Dietz', course: 'AP World History' },
    { date: [4, 10], time: '08:00', student: 'Jackson Price', course: 'AP World History' },
    { date: [4, 10], time: '08:35', student: 'Ali Romman', course: 'AP Human Geography' },
    { date: [4, 10], time: '09:05', student: 'Benny Valles', course: 'AP Human Geography' },

    // Week of Apr 13
    { date: [4, 15], time: '08:00', student: 'Zayen Szpitalak', course: 'AP Human Geography' },
    { date: [4, 15], time: '08:35', student: 'Stella Cole', course: 'AP World History' },
    { date: [4, 16], time: '08:20', student: 'Gus Castillo', course: 'AP Human Geography' },
    { date: [4, 16], time: '08:35', student: 'Branson Pfiester', course: 'AP Human Geography' },
    { date: [4, 16], time: '09:35', student: 'Emma Cotner', course: 'AP World History' },
    { date: [4, 17], time: '08:00', student: 'Saeed Tarawneh', course: 'AP World History' },
    { date: [4, 17], time: '08:35', student: 'Vera Li', course: 'AP Human Geography' },
    { date: [4, 17], time: '09:05', student: 'Emily Smith', course: 'AP US Government' },

    // Week of Apr 20 - SPRING BREAK - No calls

    // Week of Apr 27
    { date: [4, 28], time: '08:00', student: 'Stella Cole', course: 'AP World History' },
    { date: [4, 29], time: '08:00', student: 'Boris Dudarev', course: 'AP Human Geography' },
    { date: [4, 29], time: '08:35', student: 'Sydney Barba', course: 'AP Human Geography' },
    { date: [4, 29], time: '09:05', student: 'Zayen Szpitalak', course: 'AP Human Geography' },
    { date: [4, 29], time: '09:40', student: 'Branson Pfiester', course: 'AP Human Geography' },
    { date: [4, 30], time: '08:20', student: 'Gus Castillo', course: 'AP Human Geography' },
    { date: [4, 30], time: '09:35', student: 'Emma Cotner', course: 'AP World History' },
    { date: [5, 1], time: '08:00', student: 'Saeed Tarawneh', course: 'AP World History' },
    { date: [5, 1], time: '08:35', student: 'Paty Margain-Junco', course: 'AP US History' },
    { date: [5, 1], time: '09:05', student: 'Michael Cai', course: 'AP World History' }
  ];

  let created = 0;
  let errors = [];

  // Set script timezone to Central
  const scriptTimeZone = Session.getScriptTimeZone();
  Logger.log(`Script timezone: ${scriptTimeZone}`);
  Logger.log(`Creating events in: ${TIMEZONE} (US Central)`);

  calls.forEach(call => {
    try {
      const [month, day] = call.date;
      const [hour, minute] = call.time.split(':').map(Number);

      // Create date string in Central Time and parse it
      const dateStr = `${YEAR}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}T${String(hour).padStart(2,'0')}:${String(minute).padStart(2,'0')}:00`;

      // Use Utilities to create timezone-aware dates
      const startTime = new Date(Utilities.formatDate(
        new Date(dateStr),
        TIMEZONE,
        "yyyy-MM-dd'T'HH:mm:ss"
      ));

      // Alternative: Create event using calendar's createEvent with explicit times
      // The times below are interpreted in Central Time
      const startDateTime = Utilities.parseDate(dateStr, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ss");
      const endDateTime = new Date(startDateTime.getTime() + CALL_DURATION_MINUTES * 60 * 1000);

      const title = `AP Coaching: ${call.student} (${call.course})`;
      const description = `AP Exam Coaching Call\n\nStudent: ${call.student}\nCourse: ${call.course}\nTimezone: US Central (Austin, TX)\n\nPrepared by coaching system.`;

      const studentEmail = studentEmails[call.student];

      const event = calendar.createEvent(title, startDateTime, endDateTime, {
        description: description,
        guests: studentEmail,
        sendInvites: true
      });

      created++;
      Logger.log(`Created: ${title} on ${Utilities.formatDate(startDateTime, TIMEZONE, "EEE MMM dd yyyy HH:mm")} Central`);

    } catch (e) {
      errors.push(`${call.student} on ${call.date}: ${e.message}`);
    }
  });

  Logger.log(`\n=== SUMMARY ===`);
  Logger.log(`Created: ${created} events`);
  Logger.log(`Errors: ${errors.length}`);
  if (errors.length > 0) {
    Logger.log(`Error details: ${errors.join('\n')}`);
  }

  // Show completion dialog
  const ui = SpreadsheetApp.getUi ? SpreadsheetApp.getUi() : null;
  if (ui) {
    ui.alert(`Created ${created} coaching call events!\n\nCheck the Logs (View > Logs) for details.`);
  }
}

/**
 * Optional: Delete all coaching events (use with caution!)
 */
function deleteCoachingEvents() {
  const calendar = CalendarApp.getDefaultCalendar();
  const startDate = new Date(2026, 2, 1); // March 1, 2026
  const endDate = new Date(2026, 4, 15);   // May 15, 2026

  const events = calendar.getEvents(startDate, endDate);
  let deleted = 0;

  events.forEach(event => {
    if (event.getTitle().startsWith('AP Coaching:')) {
      event.deleteEvent();
      deleted++;
    }
  });

  Logger.log(`Deleted ${deleted} coaching events.`);
}
