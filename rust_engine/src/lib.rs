use pyo3::prelude::*;
use rayon::prelude::*;

// ──────────────────────────────────────────────────────────────
// Euclidean distance helpers
// ──────────────────────────────────────────────────────────────

#[inline]
fn euclidean_sq(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b.iter()).map(|(x, y)| (x - y).powi(2)).sum()
}

// ──────────────────────────────────────────────────────────────
// Public API
// ──────────────────────────────────────────────────────────────

/// For a single query vector, find the index of the closest row in hist_matrix.
/// Returns (best_index, min_euclidean_distance).
/// Used when calling one-shot from Python without batching.
#[pyfunction]
fn find_closest_match(
    query: Vec<f64>,
    hist_matrix: Vec<Vec<f64>>,
) -> PyResult<(usize, f64)> {
    if hist_matrix.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("hist_matrix is empty"));
    }

    let (best_idx, min_dist) = hist_matrix
        .par_iter()
        .enumerate()
        .map(|(i, row)| (i, euclidean_sq(&query, row)))
        .reduce(
            || (0, f64::INFINITY),
            |(bi, bd), (i, d)| if d < bd { (i, d) } else { (bi, bd) },
        );

    Ok((best_idx, min_dist.sqrt()))
}

/// Batch version: computes nearest-neighbour predictions for every row in
/// feature_matrix in a single call — eliminates the Python for-loop.
///
/// Arguments:
///   feature_matrix  — 2-D array [n_rows × n_features], row-major
///   future_returns  — 1-D array [n_rows], outcome label for each row
///   forward_prediction — number of candles ahead (skip window)
///   vault_lookback  — max historical window size
///
/// Returns a 1-D predictions array of length n_rows:
///   predictions[i] = future_returns[argmin_euclidean(feature_matrix[i],
///                                    feature_matrix[start..end])]
///   where end = i - forward_prediction and start = max(0, end - vault_lookback)
///
/// Rows where end <= 0 have prediction 0.0.
/// Parallelised over all rows using rayon.
#[pyfunction]
fn find_all_closest_matches(
    feature_matrix: Vec<Vec<f64>>,
    future_returns: Vec<f64>,
    forward_prediction: usize,
    vault_lookback: usize,
) -> PyResult<Vec<f64>> {
    let n = feature_matrix.len();
    if n != future_returns.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "feature_matrix and future_returns must have the same length",
        ));
    }

    let predictions: Vec<f64> = (0..n)
        .into_par_iter()
        .map(|i| {
            if i < forward_prediction {
                return 0.0;
            }
            let end_idx = i - forward_prediction;
            if end_idx == 0 {
                return 0.0;
            }
            let start_idx = if end_idx > vault_lookback {
                end_idx - vault_lookback
            } else {
                0
            };

            let query = &feature_matrix[i];
            let (best_offset, _) = feature_matrix[start_idx..end_idx]
                .iter()
                .enumerate()
                .map(|(j, row)| (j, euclidean_sq(query, row)))
                .fold((0usize, f64::INFINITY), |(bi, bd), (j, d)| {
                    if d < bd { (j, d) } else { (bi, bd) }
                });

            future_returns[start_idx + best_offset]
        })
        .collect();

    Ok(predictions)
}

/// Returns version information for the rust_engine module.
#[pyfunction]
fn version() -> String {
    format!(
        "rust_engine v{} (Rust/PyO3/rayon, compiled {})",
        env!("CARGO_PKG_VERSION"),
        env!("CARGO_PKG_NAME"),
    )
}

// ──────────────────────────────────────────────────────────────
// Module registration
// ──────────────────────────────────────────────────────────────

#[pymodule]
fn rust_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(find_closest_match, m)?)?;
    m.add_function(wrap_pyfunction!(find_all_closest_matches, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}

// ──────────────────────────────────────────────────────────────
// Tests
// ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_matrix(rows: Vec<Vec<f64>>) -> Vec<Vec<f64>> {
        rows
    }

    #[test]
    fn test_find_closest_match_identity() {
        let hist = make_matrix(vec![
            vec![1.0, 2.0, 3.0],
            vec![4.0, 5.0, 6.0],
            vec![7.0, 8.0, 9.0],
        ]);
        let query = vec![4.0, 5.0, 6.0];
        let (idx, dist) = find_closest_match(query, hist).unwrap();
        assert_eq!(idx, 1);
        assert!(dist < 1e-9, "Expected ~0 distance, got {dist}");
    }

    #[test]
    fn test_find_all_closest_matches_basic() {
        let feat = make_matrix(vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
            vec![3.0, 0.0],
            vec![1.5, 0.0], // query: closest to index 1 or 2
        ]);
        let returns = vec![0.01, 0.02, 0.03, 0.04, 0.05_f64];
        // forward_prediction=1, vault_lookback=100
        let preds = find_all_closest_matches(feat, returns, 1, 100).unwrap();
        // i=4 → end=3, hist=feat[0..3], closest to [1.5,0] is feat[1]=[1.0,0] (d=0.25) or feat[2]=[2.0,0] (d=0.25)
        // both same distance → first wins
        assert!(preds[4] > 0.0, "Expected non-zero prediction at index 4");
        assert_eq!(preds[0], 0.0, "Expected 0.0 for first row");
        assert_eq!(preds[1], 0.0, "Expected 0.0 for second row (i<forward_prediction)");
    }

    #[test]
    fn test_find_all_closest_matches_length_mismatch() {
        let feat = make_matrix(vec![vec![1.0], vec![2.0]]);
        let returns = vec![0.01_f64]; // wrong length
        let result = find_all_closest_matches(feat, returns, 1, 100);
        assert!(result.is_err());
    }
}
