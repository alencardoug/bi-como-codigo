// The session of Evidence's encrypted page: 0 before login, raised by Login once p01.rows exists.
// A store imported by the page, not a variable of its script: Evidence declares the page's queries
// before that script runs, and a query naming a script variable reads it before it exists.
import { writable } from 'svelte/store';

export const session = writable(0);
