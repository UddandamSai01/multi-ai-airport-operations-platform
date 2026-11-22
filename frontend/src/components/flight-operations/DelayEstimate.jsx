import React, { useEffect, useState } from "react";
import { AlertTriangle, Info, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import { getFlightDelayEstimate } from "../../services/analysisApi";

const LIMITATIONS =
  "Estimates come from a model trained on one year (2023) of flights between 10 US airports. " +
  "Other airports and airlines are less reliable, forecast weather is less accurate than " +
  "historical weather, and overall accuracy is moderate. Use as decision support only.";

const BADGE = {
  Low: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  Medium: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  High: "bg-rose-500/20 text-rose-300 border-rose-500/40",
};

const errorMessage = (error) => {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;

  if (status === 503) {
    return "The delay model is unavailable right now. The rest of the application is not affected.";
  }
  if (status === 404) {
    return "This flight was not found, so no delay estimate can be shown.";
  }
  if (status === 422) {
    return typeof detail === "string"
      ? detail
      : "This flight cannot be converted for the delay model.";
  }
  return "Unable to retrieve the delay estimate.";
};

const formatValue = (value) => {
  if (value === null || value === undefined) return "n/a";
  if (typeof value === "number") return Number.isInteger(value) ? value : value.toFixed(2);
  return String(value);
};

export const DelayEstimate = ({ flight }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const flightKey = flight?.id ?? flight?.flightNumber;

  useEffect(() => {
    let cancelled = false;

    if (!flightKey) {
      setData(null);
      setError(null);
      setLoading(false);
      return undefined;
    }

    const load = async () => {
      setLoading(true);
      setError(null);
      setData(null);

      try {
        const result = await getFlightDelayEstimate(flightKey);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [flightKey]);

  const probability =
    typeof data?.delay_probability === "number"
      ? Math.round(data.delay_probability * 100)
      : null;

  return (
    <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-cyan-400" />
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
          Predicted delay risk (ML estimate)
        </h4>
        <span className="ml-auto rounded border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-cyan-300">
          Estimate
        </span>
      </div>

      {loading && (
        <div className="text-xs text-cyan-400">Loading delay estimate...</div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {!loading && !error && !data && (
        <div className="text-xs text-slate-400">
          No delay estimate available for this flight.
        </div>
      )}

      {!loading && !error && data && (
        <>
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <div className="font-mono text-3xl font-black text-white">
                {probability !== null ? `${probability}%` : "n/a"}
              </div>
              <div className="text-[11px] text-slate-400">
                chance of a delay over 15 min (estimate)
              </div>
            </div>

            <div>
              <div className="font-mono text-xl font-bold text-white">
                {typeof data.expected_delay_minutes === "number"
                  ? `${Math.round(data.expected_delay_minutes)} min`
                  : "n/a"}
              </div>
              <div className="text-[11px] text-slate-400">
                expected delay (estimate)
              </div>
            </div>

            <span
              className={`rounded border px-2.5 py-0.5 text-xs font-bold uppercase ${
                BADGE[data.risk_level] || BADGE.Low
              }`}
            >
              {data.risk_level || "Unknown"} risk
            </span>
          </div>

          <div className="text-[11px] text-slate-400">
            Weather source:{" "}
            <span className="text-slate-200">
              {data.weather_source === "forecast"
                ? "forecast"
                : "unavailable (estimate uses historical patterns only)"}
            </span>
          </div>

          {Array.isArray(data.top_factors) && data.top_factors.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Top factors
              </div>
              {data.top_factors.map((factor, index) => {
                const increases = String(factor.effect || "").includes("increases");
                return (
                  <div
                    key={index}
                    className="flex items-center gap-2 rounded border border-slate-800 bg-slate-900/60 px-2 py-1.5 text-xs"
                  >
                    {increases ? (
                      <TrendingUp className="h-3.5 w-3.5 shrink-0 text-rose-400" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                    )}
                    <span className="text-slate-200">{factor.factor}</span>
                    <span className="font-mono text-slate-500">
                      ({formatValue(factor.value)})
                    </span>
                    <span
                      className={`ml-auto text-[10px] ${
                        increases ? "text-rose-300" : "text-emerald-300"
                      }`}
                    >
                      {factor.effect}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {Array.isArray(data.warnings) &&
            data.warnings.map((warning, index) => (
              <div
                key={index}
                className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-300"
              >
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {warning}
              </div>
            ))}

          <div className="flex items-start gap-2 text-[11px] leading-relaxed text-slate-500">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              {data.limitations || LIMITATIONS}
              {data.disclaimer ? ` ${data.disclaimer}` : ""}
            </span>
          </div>
        </>
      )}
    </div>
  );
};

export default DelayEstimate;