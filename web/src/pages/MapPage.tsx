import { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { api, CustomerGeoLocation } from "../lib/api";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { MapPin, Navigation, Loader2, AlertCircle } from "lucide-react";
import "leaflet/dist/leaflet.css";

// Fix Leaflet default icon paths (broken in bundlers)
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

// @ts-expect-error Leaflet default icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl });

function AutoFitBounds({ locations }: { locations: CustomerGeoLocation[] }) {
	const map = useMap();
	useEffect(() => {
		const withCoords = locations.filter((l) => l.latitude && l.longitude);
		if (withCoords.length === 0) return;
		const bounds = L.latLngBounds(
			withCoords.map((l) => [l.latitude!, l.longitude!] as [number, number]),
		);
		map.fitBounds(bounds, { padding: [50, 50] });
	}, [locations, map]);
	return null;
}

export default function MapPage() {
	const [locations, setLocations] = useState<CustomerGeoLocation[]>([]);
	const [loading, setLoading] = useState(true);
	const [geocoding, setGeocoding] = useState(false);
	const [geocodingSingle, setGeocodingSingle] = useState<string | null>(null);
	const [error, setError] = useState("");

	const loadLocations = async () => {
		setLoading(true);
		setError("");
		try {
			const res = await api.customers.geolocations.list();
			setLocations(res.locations);
		} catch (e: any) {
			setError(e.message);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		loadLocations();
	}, []);

	const handleGeocodeAll = async () => {
		setGeocoding(true);
		try {
			await api.customers.geolocations.geocodeAll();
			await loadLocations();
		} catch (e: any) {
			setError(e.message);
		} finally {
			setGeocoding(false);
		}
	};

	const handleGeocodeSingle = async (customerId: string) => {
		setGeocodingSingle(customerId);
		try {
			await api.customers.geolocations.geocode(customerId);
			await loadLocations();
		} catch (e: any) {
			setError(e.message);
		} finally {
			setGeocodingSingle(null);
		}
	};

	const withCoords = locations.filter((l) => l.latitude && l.longitude);
	const withoutCoords = locations.filter(
		(l) => !l.has_location && (l.address_line1 || l.city),
	);

	return (
		<div className="space-y-6 p-6">
			<div className="flex items-start justify-between gap-2 flex-wrap">
				<div>
					<h1 className="text-2xl font-bold flex items-center gap-2">
						<MapPin className="h-6 w-6 text-primary" />
						Customer Map
					</h1>
					<p className="text-sm text-muted-foreground mt-1">
						{withCoords.length} of {locations.length} customers with locations
					</p>
				</div>
				<div className="flex gap-2">
					<Button
						variant="outline"
						size="sm"
						onClick={loadLocations}
						disabled={loading}
					>
						<Loader2
							className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`}
						/>
						Refresh
					</Button>
					<Button
						size="sm"
						onClick={handleGeocodeAll}
						disabled={geocoding || withoutCoords.length === 0}
					>
						{geocoding ? (
							<Loader2 className="h-4 w-4 mr-1 animate-spin" />
						) : (
							<Navigation className="h-4 w-4 mr-1" />
						)}
						Geocode All ({withoutCoords.length})
					</Button>
				</div>
			</div>

			{error && (
				<div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-4 py-2 rounded-md">
					<AlertCircle className="h-4 w-4" />
					{error}
				</div>
			)}

			{loading ? (
				<div className="flex items-center justify-center h-[500px]">
					<Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
				</div>
			) : (
				<div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
					{/* Map */}
					<div className="lg:col-span-3 rounded-lg overflow-hidden border border-border h-[600px]">
						{withCoords.length > 0 ? (
							<MapContainer
								center={[39.8283, -98.5795]}
								zoom={4}
								className="h-full w-full"
								scrollWheelZoom={true}
							>
								<TileLayer
									attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
									url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
								/>
								<AutoFitBounds locations={locations} />
								{withCoords.map((loc) => (
									<Marker
										key={loc.id}
										position={[loc.latitude!, loc.longitude!]}
									>
										<Popup>
											<div className="text-sm min-w-[180px]">
												<p className="font-semibold text-base">{loc.name}</p>
												{loc.company && (
													<p className="text-muted-foreground">{loc.company}</p>
												)}
												{loc.address && <p className="mt-1">{loc.address}</p>}
												{loc.email && (
													<p className="text-xs mt-1">{loc.email}</p>
												)}
												{loc.phone && <p className="text-xs">{loc.phone}</p>}
											</div>
										</Popup>
									</Marker>
								))}
							</MapContainer>
						) : (
							<div className="h-full flex items-center justify-center text-muted-foreground">
								<div className="text-center">
									<MapPin className="h-12 w-12 mx-auto mb-2 opacity-50" />
									<p>No customer locations yet</p>
									<p className="text-xs mt-1">
										Geocode customers with addresses to see them on the map
									</p>
								</div>
							</div>
						)}
					</div>

					{/* Sidebar */}
					<div className="space-y-3 max-h-[600px] overflow-y-auto">
						<h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
							Customers without location
						</h3>
						{withoutCoords.length === 0 ? (
							<p className="text-sm text-muted-foreground">
								All customers geocoded! 🎉
							</p>
						) : (
							withoutCoords.slice(0, 50).map((loc) => (
								<Card key={loc.id} className="border-border/50">
									<CardContent className="p-3">
										<div className="flex items-start justify-between gap-2">
											<div className="min-w-0">
												<p className="text-sm font-medium truncate">
													{loc.name}
												</p>
												{loc.address && (
													<p className="text-xs text-muted-foreground truncate">
														{loc.address}
													</p>
												)}
												{!loc.address && (
													<p className="text-xs text-destructive">
														No address on file
													</p>
												)}
											</div>
											{loc.address && (
												<Button
													variant="ghost"
													size="sm"
													className="shrink-0 h-7 w-7 p-0"
													onClick={() => handleGeocodeSingle(loc.id)}
													disabled={geocodingSingle === loc.id}
												>
													{geocodingSingle === loc.id ? (
														<Loader2 className="h-3 w-3 animate-spin" />
													) : (
														<Navigation className="h-3 w-3" />
													)}
												</Button>
											)}
										</div>
									</CardContent>
								</Card>
							))
						)}
						{withoutCoords.length > 50 && (
							<p className="text-xs text-muted-foreground">
								+{withoutCoords.length - 50} more without addresses
							</p>
						)}
					</div>
				</div>
			)}
		</div>
	);
}
