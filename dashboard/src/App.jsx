import BotDemo from "./components/BotDemo";
import DistrictMap from "./components/DistrictMap";
import MandiPrices from "./components/MandiPrices";

export default function App() {
  return (
    <main>
      <h1>Rythu Mitra Dashboard</h1>
      <p>Scaffold for district map, live mandi prices, and bot demo.</p>
      <DistrictMap />
      <MandiPrices />
      <BotDemo />
    </main>
  );
}
