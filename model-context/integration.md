# Frontend Integration Guide for Refactored Trademark API

## Overview

The backend API has been completely refactored to follow a modular, sequential approach that better aligns with UK/EU legal reasoning for trademark oppositions. This document outlines the necessary changes required for frontend integration.

## Key Changes

The API has moved from a single monolithic endpoint (`/predict`) to three separate, sequential endpoints:

1. **`/mark_similarity`** - Assesses similarity between two wordmarks
2. **`/gs_similarity`** - Evaluates a single pair of goods/services with knowledge of the mark similarity
3. **`/case_prediction`** - Aggregates results and determines overall opposition outcome

This change provides more detailed assessments at each step and allows for concurrent processing of multiple goods/services comparisons.

## Required Type Updates

### Update `trademark.ts`

The following new TypeScript interfaces must be added to `src/types/trademark.ts`:

```typescript
// New interface for mark similarity request
export interface MarkSimilarityRequest {
  applicant: TrademarkMark;
  opponent: TrademarkMark;
}

// New interface for mark similarity response
export interface MarkSimilarityOutput {
  visual: MarkSimilarityEnum;
  aural: MarkSimilarityEnum;
  conceptual: MarkSimilarityEnum;
  overall: MarkSimilarityEnum;
  reasoning?: string; // Optional LLM reasoning
}

// New interface for goods/services with likelihood of confusion
export interface GoodServiceLikelihoodOutput {
  applicant_good: GoodOrService;
  opponent_good: GoodOrService;
  are_competitive: boolean;
  are_complementary: boolean;
  similarity_score: number; // 0.0 to 1.0
  likelihood_of_confusion: boolean;
  confusion_type?: "direct" | "indirect"; // Only if likelihood_of_confusion is true
}

// Request for goods/services similarity
export interface GsSimilarityRequest {
  applicant_good: GoodOrService;
  opponent_good: GoodOrService;
  mark_similarity: MarkSimilarityOutput; // The output from /mark_similarity
}

// Request for case prediction
export interface CasePredictionRequest {
  mark_similarity: MarkSimilarityOutput;
  goods_services_likelihoods: GoodServiceLikelihoodOutput[];
}

// Updated case prediction result (replacing the old CasePrediction)
export interface CasePredictionResult {
  mark_similarity: MarkSimilarityOutput;
  goods_services_likelihoods: GoodServiceLikelihoodOutput[];
  opposition_outcome: OppositionOutcome;
}
```

### Type Changes to Note

1. The legacy `CasePrediction` interface should be replaced with the new `CasePredictionResult` interface.
2. The `GoodServiceComparison` type is replaced by the more informative `GoodServiceLikelihoodOutput`.
3. `likelihood_of_confusion` is now a property for each goods/services pair, not a top-level property.

## API Integration Updates

### Update `src/lib/api.ts`

The API integration needs to be completely updated to support the new endpoints:

```typescript
import { 
  MarkSimilarityRequest, MarkSimilarityOutput, 
  GsSimilarityRequest, GoodServiceLikelihoodOutput,
  CasePredictionRequest, CasePredictionResult,
  PredictionRequest 
} from "@/types/trademark";
import { getAuth } from "firebase/auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// Helper function to get Firebase token and handle API calls
async function callProtectedApi<TRequest, TResponse>(
  endpoint: string,
  requestData: TRequest
): Promise<TResponse> {
  if (!API_BASE_URL) {
    throw new Error("API base URL is not configured in environment variables.");
  }

  // Get Firebase ID token for the current user
  const auth = getAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new Error("User is not logged in. Please log in to use this feature.");
  }
  const idToken = await user.getIdToken();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${idToken}`,
    },
    body: JSON.stringify(requestData),
  });

  if (!response.ok) {
    // Attempt to parse error details from the response body
    let errorBody;
    try {
      errorBody = await response.json();
    } catch (e) {
      // Ignore if the body isn't valid JSON
    }
    console.error("API Error:", response.status, errorBody);
    throw new Error(
      `API request failed with status ${response.status}: ${
        errorBody?.detail || response.statusText
      }`
    );
  }

  return response.json() as Promise<TResponse>;
}

// Step 1: Compare marks
export const getMarkSimilarity = async (
  request: MarkSimilarityRequest
): Promise<MarkSimilarityOutput> => {
  return callProtectedApi<MarkSimilarityRequest, MarkSimilarityOutput>("/mark_similarity", request);
};

// Step 2: Compare a single goods/services pair
export const getGoodServiceSimilarity = async (
  request: GsSimilarityRequest
): Promise<GoodServiceLikelihoodOutput> => {
  return callProtectedApi<GsSimilarityRequest, GoodServiceLikelihoodOutput>("/gs_similarity", request);
};

// Step 3: Get final case prediction
export const getCasePrediction = async (
  request: CasePredictionRequest
): Promise<CasePredictionResult> => {
  return callProtectedApi<CasePredictionRequest, CasePredictionResult>("/case_prediction", request);
};

// Backwards compatibility wrapper for legacy code (if needed)
export const predictTrademarkOpposition = async (
  requestData: PredictionRequest
): Promise<CasePredictionResult> => {
  console.warn("predictTrademarkOpposition is deprecated. Use the new modular API endpoints.");
  
  // Step 1: Mark similarity
  const markSimilarityRequest: MarkSimilarityRequest = {
    applicant: requestData.applicant,
    opponent: requestData.opponent
  };
  const markSimilarity = await getMarkSimilarity(markSimilarityRequest);
  
  // Step 2: Process each goods/services pair
  const gsLikelihoodPromises = requestData.applicant_goods.flatMap(applicantGood => 
    requestData.opponent_goods.map(opponentGood => {
      const gsSimilarityRequest: GsSimilarityRequest = {
        applicant_good: applicantGood,
        opponent_good: opponentGood,
        mark_similarity: markSimilarity
      };
      return getGoodServiceSimilarity(gsSimilarityRequest);
    })
  );
  
  const gsLikelihoods = await Promise.all(gsLikelihoodPromises);
  
  // Step 3: Get case prediction
  const casePredictionRequest: CasePredictionRequest = {
    mark_similarity: markSimilarity,
    goods_services_likelihoods: gsLikelihoods
  };
  
  return getCasePrediction(casePredictionRequest);
};

// Health check function remains unchanged
export const checkApiHealth = async (): Promise<{ status: string }> => {
  if (!API_BASE_URL) {
    throw new Error("API base URL is not configured in environment variables.");
  }
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`API health check failed with status ${response.status}`);
  }
  return response.json() as Promise<{ status: string }>;
};
```

## Create New Custom Hooks

Create the following hooks in the `src/hooks` directory:

### 1. `useMarkSimilarity.ts`

```typescript
import { useMutation, UseMutationOptions } from "@tanstack/react-query";
import { getMarkSimilarity } from "@/lib/api";
import { MarkSimilarityRequest, MarkSimilarityOutput } from "@/types/trademark";

type MarkSimilarityError = Error;

type UseMarkSimilarityOptions = Omit<
  UseMutationOptions<
    MarkSimilarityOutput,
    MarkSimilarityError,
    MarkSimilarityRequest
  >,
  'mutationFn'
>;

export const useMarkSimilarity = (options?: UseMarkSimilarityOptions) => {
  return useMutation<MarkSimilarityOutput, MarkSimilarityError, MarkSimilarityRequest>({
    mutationFn: getMarkSimilarity,
    ...options,
  });
};
```

### 2. `useGoodServiceSimilarity.ts`

```typescript
import { useMutation, UseMutationOptions } from "@tanstack/react-query";
import { getGoodServiceSimilarity } from "@/lib/api";
import { GsSimilarityRequest, GoodServiceLikelihoodOutput } from "@/types/trademark";

type GsSimilarityError = Error;

type UseGoodServiceSimilarityOptions = Omit<
  UseMutationOptions<
    GoodServiceLikelihoodOutput,
    GsSimilarityError,
    GsSimilarityRequest
  >,
  'mutationFn'
>;

export const useGoodServiceSimilarity = (options?: UseGoodServiceSimilarityOptions) => {
  return useMutation<GoodServiceLikelihoodOutput, GsSimilarityError, GsSimilarityRequest>({
    mutationFn: getGoodServiceSimilarity,
    ...options,
  });
};
```

### 3. `useCasePrediction.ts`

```typescript
import { useMutation, UseMutationOptions } from "@tanstack/react-query";
import { getCasePrediction } from "@/lib/api";
import { CasePredictionRequest, CasePredictionResult } from "@/types/trademark";

type CasePredictionError = Error;

type UseCasePredictionOptions = Omit<
  UseMutationOptions<
    CasePredictionResult,
    CasePredictionError,
    CasePredictionRequest
  >,
  'mutationFn'
>;

export const useCasePrediction = (options?: UseCasePredictionOptions) => {
  return useMutation<CasePredictionResult, CasePredictionError, CasePredictionRequest>({
    mutationFn: getCasePrediction,
    ...options,
  });
};
```

### 4. Update `useTrademarkPrediction.ts`

```typescript
import { useMutation, UseMutationOptions } from "@tanstack/react-query";
import { predictTrademarkOpposition } from "@/lib/api";
import { PredictionRequest, CasePredictionResult } from "@/types/trademark";

// Define the type for the error, which is likely an Error object
type PredictionError = Error;

// Define options type if you want to allow customizing mutation behavior from the component
type UseTrademarkPredictionOptions = Omit<
  UseMutationOptions<
    CasePredictionResult, // Updated return type (was CasePrediction)
    PredictionError,
    PredictionRequest
  >,
  'mutationFn'
>;

/**
 * Custom hook to manage the trademark opposition prediction API call using TanStack Query.
 * @deprecated Use the new modular hooks instead: useMarkSimilarity, useGoodServiceSimilarity, useCasePrediction
 */
export const useTrademarkPrediction = (options?: UseTrademarkPredictionOptions) => {
  return useMutation<CasePredictionResult, PredictionError, PredictionRequest>({
    mutationFn: predictTrademarkOpposition,
    ...options,
  });
};
```

## Updating the OppositionPrediction Component

The `OppositionPrediction.tsx` component needs updates to handle the new API flow. Here's an approach to implement the changes:

1. Import the new hooks and types
2. Create state for each step of the prediction process
3. Implement the multi-step prediction flow
4. Update the UI to display the new result structure

A sample implementation approach:

```typescript
// In OppositionPrediction.tsx
import { useState } from "react";
import { useMarkSimilarity } from "@/hooks/useMarkSimilarity";
import { useGoodServiceSimilarity } from "@/hooks/useGoodServiceSimilarity";
import { useCasePrediction } from "@/hooks/useCasePrediction";
import { 
  MarkSimilarityOutput, 
  GoodServiceLikelihoodOutput,
  CasePredictionResult
} from "@/types/trademark";

// Add state for multi-step prediction
const [markSimilarity, setMarkSimilarity] = useState<MarkSimilarityOutput | null>(null);
const [goodsServiceLikelihoods, setGoodsServiceLikelihoods] = useState<GoodServiceLikelihoodOutput[]>([]);
const [predictionResult, setPredictionResult] = useState<CasePredictionResult | null>(null);

// Add hooks for each API
const markSimilarityMutation = useMarkSimilarity();
const goodServiceSimilarityMutation = useGoodServiceSimilarity();
const casePredictionMutation = useCasePrediction();

// Implement the multi-step prediction flow
const handlePrediction = async () => {
  try {
    // Step 1: Get mark similarity
    const markSimilarityResult = await markSimilarityMutation.mutateAsync({
      applicant: { 
        wordmark: request.applicant.wordmark,
        is_registered: false 
      },
      opponent: {
        wordmark: request.opponent.wordmark,
        is_registered: !!request.opponent.is_registered,
        ...(request.opponent.is_registered && { registration_number: request.opponent.registration_number })
      }
    });
    
    setMarkSimilarity(markSimilarityResult);
    
    // Step 2: Compare each goods/services pair
    const gsPromises = request.applicant_goods.flatMap(applicantGood => 
      request.opponent_goods.map(opponentGood => 
        goodServiceSimilarityMutation.mutateAsync({
          applicant_good: {
            term: applicantGood.term,
            nice_class: parseInt(String(applicantGood.nice_class), 10)
          },
          opponent_good: {
            term: opponentGood.term,
            nice_class: parseInt(String(opponentGood.nice_class), 10)
          },
          mark_similarity: markSimilarityResult
        })
      )
    );
    
    const gsResults = await Promise.all(gsPromises);
    setGoodsServiceLikelihoods(gsResults);
    
    // Step 3: Get case prediction
    const caseResult = await casePredictionMutation.mutateAsync({
      mark_similarity: markSimilarityResult,
      goods_services_likelihoods: gsResults
    });
    
    setPredictionResult(caseResult);
  } catch (error) {
    console.error("Prediction error:", error);
    // Handle error appropriately
  }
};
```

## Displaying the New Results

Update the results section to display the new structure:

```jsx
{predictionResult && !isLoading && !predictionError && (
  <div className="space-y-6 bg-[#131722] rounded-lg border border-white/10 p-6">
    {/* Opposition outcome */}
    {predictionResult.opposition_outcome && (
      <Alert
        variant={predictionResult.opposition_outcome.result.toLowerCase().includes("fail") ? "default" : "destructive"}
        className="border-l-4"
      >
        <AlertTitle className="text-lg font-semibold">{predictionResult.opposition_outcome.result}</AlertTitle>
        <AlertDescription className="mt-1">
          <p><span className="font-medium">Confidence:</span> {(predictionResult.opposition_outcome.confidence * 100).toFixed(0)}%</p>
          <p className="mt-2">{predictionResult.opposition_outcome.reasoning}</p>
        </AlertDescription>
      </Alert>
    )}

    {/* Mark comparison */}
    {predictionResult.mark_similarity && (
      <div className="space-y-4">
        <h3 className="text-xl font-semibold text-brand">Mark Comparison</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-background p-4 rounded border border-white/10">
            <h4 className="font-medium text-base mb-1">Visual Similarity</h4>
            <p className="text-sm capitalize">{predictionResult.mark_similarity.visual || 'N/A'}</p>
          </div>
          <div className="bg-background p-4 rounded border border-white/10">
            <h4 className="font-medium text-base mb-1">Aural Similarity</h4>
            <p className="text-sm capitalize">{predictionResult.mark_similarity.aural || 'N/A'}</p>
          </div>
          <div className="bg-background p-4 rounded border border-white/10">
            <h4 className="font-medium text-base mb-1">Conceptual Similarity</h4>
            <p className="text-sm capitalize">{predictionResult.mark_similarity.conceptual || 'N/A'}</p>
          </div>
          <div className="bg-background p-4 rounded border border-white/10">
            <h4 className="font-medium text-base mb-1">Overall Mark Similarity</h4>
            <p className="text-sm capitalize">{predictionResult.mark_similarity.overall || 'N/A'}</p>
          </div>
        </div>
      </div>
    )}

    {/* Goods & Services Comparisons */}
    {predictionResult.goods_services_likelihoods && predictionResult.goods_services_likelihoods.length > 0 && (
      <div className="space-y-4">
        <h3 className="text-xl font-semibold text-brand">Goods & Services Analysis</h3>
        <div className="space-y-4">
          {predictionResult.goods_services_likelihoods.map((gs, index) => (
            <div key={index} className="bg-background p-4 rounded border border-white/10">
              <div className="flex flex-col md:flex-row justify-between gap-2 mb-3">
                <div className="flex-1">
                  <h5 className="text-xs uppercase text-text-secondary mb-1">Applicant</h5>
                  <p className="text-sm">{gs.applicant_good.term} (Class {gs.applicant_good.nice_class})</p>
                </div>
                <div className="flex-1">
                  <h5 className="text-xs uppercase text-text-secondary mb-1">Opponent</h5>
                  <p className="text-sm">{gs.opponent_good.term} (Class {gs.opponent_good.nice_class})</p>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
                <div>
                  <h5 className="text-xs uppercase text-text-secondary mb-1">Similarity</h5>
                  <p className="text-sm">{(gs.similarity_score * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <h5 className="text-xs uppercase text-text-secondary mb-1">Relationship</h5>
                  <p className="text-sm">
                    {gs.are_competitive ? "Competitive" : ""}
                    {gs.are_competitive && gs.are_complementary ? ", " : ""}
                    {gs.are_complementary ? "Complementary" : ""}
                    {!gs.are_competitive && !gs.are_complementary ? "Unrelated" : ""}
                  </p>
                </div>
                <div>
                  <h5 className="text-xs uppercase text-text-secondary mb-1">Likelihood of Confusion</h5>
                  <p className={`text-sm ${gs.likelihood_of_confusion ? "text-red-500 font-medium" : ""}`}>
                    {gs.likelihood_of_confusion ? `Yes (${gs.confusion_type})` : "No"}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
)}
```

## Migration Strategy

1. **Dual Support Period** (Optional):
   - Keep the legacy `predictTrademarkOpposition` function that internally uses the new endpoints
   - This allows gradual migration without breaking existing functionality

2. **Component Refactoring Steps**:
   - Update type definitions first
   - Create new hooks
   - Refactor components one by one to use the new API flow
   - Test thoroughly at each step

3. **Recommended Implementation Sequence**:
   1. Update `trademark.ts` with new types
   2. Add new API functions in `api.ts`
   3. Create new hooks
   4. Update `OppositionPrediction.tsx` component
   5. Add loading indicators for each step
   6. Add error handling for each step

## Advantages of the New API

1. **More Detailed Analysis**: Each step provides focused, detailed assessment
2. **Better Performance**: Process multiple goods/services comparisons concurrently
3. **Improved User Experience**: Show progressive results as they become available
4. **Follows Legal Reasoning**: Aligns with UK/EU trademark legal assessment process

## Environment Configuration

No changes needed to environment variables. The existing `VITE_API_BASE_URL` variable works for all endpoints.

## Conclusion

This refactoring provides a more modular, scalable API structure that follows legal reasoning more closely. While it requires significant changes to the frontend integration code, it offers much more detailed analysis and better performance by enabling concurrent processing of multiple goods/services pairs. 