import api from "../api";

// Estimate for one flight (database id or flight number).
export const getFlightDelayEstimate = async (flightId) => {
  const response = await api.get(
    `/api/flights/${encodeURIComponent(flightId)}/delayestimate`
  );
  return response.data;
};

// Estimates for 1 to 10 flights (flight numbers).
export const runDelayAnalysis = async (flightNumbers) => {
  const response = await api.post("/api/analysis/delay-estimates", {
    flight_numbers: flightNumbers,
  });
  return response.data;
};